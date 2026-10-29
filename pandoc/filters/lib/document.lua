-- document (Typst only): a PDF document assembled by `studykit pdf` (docs/architecture.md
-- §3.3), passed with -M sk-doc=<kind> (overview, summary, exercises, exercises-blank, mc,
-- exam, exam-solutions, cheatsheet, plan) and -M sk-file=_build/typ/<doc>.md.
--
-- The top level of an assembled document holds only generated blocks, and every course
-- file sits inside a part:
--
--   :::::: {.sk-part file="exercises/rc-filter/ex-rc-tp-grenzfrequenz.md" lines="40-71"
--           first="12" number="3.1" hints="appendix" solution="appendix"}
--   …the file's body, frontmatter stripped…
--   ::::::
--
-- A part is checked and rendered like the file on its own: its kind comes from `file`,
-- guard runs on it as the root of that file, and `lines` (its lines in the assembled
-- file) with `first` (the file line of the first of them) let the fence scan report the
-- course file and its own line. `hints` and `solution` (inline | appendix | none, default
-- sk-solutions) say where its hints and its solution or MC keys go; `number` and `title`
-- name it in the appendix.
--
-- Generated blocks (plain text is escaped by the assembler; math is checked and converted
-- like any other):
--   # / ## / ###                  headings
--   paragraphs                    text and inline math
--   ::: {.sk-gen fn="info"}       one ```json block → #sk-info(…, labels: sk-l); also
--                                 fn="cover" → #sk-exam-cover(…), fn="plan" → #sk-plan(…)
--   ::: sk-meta                   a small line under a heading → #sk-meta[…]
--   ::: sk-objectives             a bullet list → #sk-objectives(labels: sk-l)[…]
--   ::: {.sk-rubric points="5;5" total="10"}   a bullet list, one criterion per point
--   ::: sk-answers                a loose list, two paragraphs per item: label, value
--   :::::::: sk-unit              generated blocks and a part kept on one page (an
--                                 exercise with its heading) → #sk-unit[…]
-- sk-rubric and sk-answers belong to the part before them and go where its solution went
-- (lib/solutions.lua: inline, into its appendix entry, or nowhere). The cheat sheet ends
-- with `#metadata("cs-end") <cs-end>`, which the page-fit loop measures.

local guard = require 'lib.guard'
local solutions = require 'lib.solutions'

local M = {}

local MODES = { inline = true, appendix = true, none = true }
local GENERATORS = { info = 'sk-info', cover = 'sk-exam-cover', plan = 'sk-plan' }
local KINDS = {
  overview = true,
  summary = true,
  exercises = true,
  ['exercises-blank'] = true,
  mc = true,
  exam = true,
  ['exam-solutions'] = true,
  cheatsheet = true,
  plan = true,
}
local FIX = 'build PDF documents with `studykit pdf`, which writes this file'

local function fail(ctx, message)
  ctx:fail('SK-PANDOC-FAIL', message, FIX)
end

---------------------------------------------------------------------------------------
-- JSON data → Typst values (strings stay strings, so no text is ever read as markup)
---------------------------------------------------------------------------------------

local function typst_value(ctx, v)
  if v == nil or v == pandoc.json.null then
    return 'none'
  end
  local t = type(v)
  if t == 'boolean' then
    return v and 'true' or 'false'
  elseif t == 'number' then
    local i = math.tointeger(v)
    return i and tostring(i) or string.format('%.12g', v)
  elseif t == 'string' then
    return ctx.typst_str(v)
  elseif t == 'table' and pandoc.utils.type(v) == 'List' then
    local parts = {}
    for _, x in ipairs(v) do
      table.insert(parts, typst_value(ctx, x))
    end
    return '(' .. table.concat(parts, ', ') .. (#parts == 1 and ',' or '') .. ')'
  elseif t == 'table' then
    local keys = {}
    for k, _ in pairs(v) do
      table.insert(keys, k)
    end
    table.sort(keys)
    if #keys == 0 then
      return '(:)'
    end
    local parts = {}
    for _, k in ipairs(keys) do
      table.insert(parts, ctx.typst_str(k) .. ': ' .. typst_value(ctx, v[k]))
    end
    return '(' .. table.concat(parts, ', ') .. ')'
  end
  return 'none'
end

---------------------------------------------------------------------------------------
-- Generated blocks
---------------------------------------------------------------------------------------

local function generator(div, ctx)
  local fn = GENERATORS[div.attributes.fn or '']
  local code = div.content[1]
  if not fn or #div.content ~= 1 or code.t ~= 'CodeBlock' then
    fail(ctx, 'sk-gen needs fn=info|cover|plan and exactly one ```json block')
    return {}
  end
  local ok, data = pcall(pandoc.json.decode, code.text, false)
  if not ok or type(data) ~= 'table' then
    fail(ctx, 'sk-gen ' .. div.attributes.fn .. ': the block is not a JSON object')
    return {}
  end
  if fn == 'sk-info' and type(data.title) == 'string' then
    ctx.doc_title = data.title
  end
  local extra = fn == 'sk-info' and ', labels: sk-l' or ''
  return { ctx.raw_typst(string.format('#%s(%s%s)', fn, typst_value(ctx, data), extra)) }
end

--- Typst markup of generated content (math converted, text escaped by pandoc).
local function markup(blocks, ctx, W)
  return ctx:typst(W.blocks(blocks, ctx, 'nested'))
end

local function bullet_items(div, ctx, name)
  local list = div.content[1]
  if #div.content ~= 1 or list.t ~= 'BulletList' then
    fail(ctx, name .. ' needs exactly one bullet list')
    return nil
  end
  return list.content
end

local function rubric(div, ctx, W)
  local items = bullet_items(div, ctx, 'sk-rubric')
  if not items then
    return {}
  end
  local points = {}
  for p in (div.attributes.points or ''):gmatch('[^;]+') do
    table.insert(points, p)
  end
  if #points ~= #items then
    fail(ctx, string.format('sk-rubric has %d criteria but %d points', #items, #points))
    return {}
  end
  local rows = {}
  for i, item in ipairs(items) do
    table.insert(rows, string.format('(%s, [%s]),', ctx.typst_str(points[i]), markup(item, ctx, W)))
  end
  local call = string.format(
    '#sk-rubric(labels: sk-l, total: %s, rows: (\n  %s\n))',
    ctx.typst_str(div.attributes.total or ''),
    table.concat(rows, '\n  ')
  )
  return solutions.attach(ctx, call)
end

local function answers(div, ctx, W)
  local items = bullet_items(div, ctx, 'sk-answers')
  if not items then
    return {}
  end
  local rows = {}
  for _, item in ipairs(items) do
    if #item ~= 2 then
      fail(ctx, 'sk-answers items need two paragraphs: label and value')
      return {}
    end
    table.insert(rows, string.format('([%s], [%s]),', markup({ item[1] }, ctx, W), markup({ item[2] }, ctx, W)))
  end
  local call = string.format('#sk-answers(labels: sk-l, rows: (\n  %s\n))', table.concat(rows, '\n  '))
  return solutions.attach(ctx, call)
end

---------------------------------------------------------------------------------------
-- Parts
---------------------------------------------------------------------------------------

--- A paragraph that is one display formula (math.lua writes it as raw Typst).
local function is_display(b)
  if b.t ~= 'Para' and b.t ~= 'Plain' then
    return false
  end
  local c = b.content
  return #c == 1
    and c[1].t == 'RawInline'
    and c[1].format == 'typst'
    and (c[1].text:match('^%$ ') or c[1].text:match('^#sk%-formulas%(')) ~= nil
end

--- A paragraph that introduces what follows ("… gilt:").
local function ends_with_colon(b)
  local last = b.t == 'Para' and b.content[#b.content]
  return last and last.t == 'Str' and last.text:match(':$') ~= nil
end

--- Keep a paragraph that ends with a colon on the page of the formula it introduces.
local function keep_intros(blocks, ctx)
  for i = 1, #blocks - 1 do
    if ends_with_colon(blocks[i]) and is_display(blocks[i + 1]) then
      blocks[i] = ctx.raw_typst('#block(sticky: true)[\n' .. ctx:typst({ blocks[i] }) .. '\n]')
    end
  end
  return blocks
end

local function split_lines(text)
  local lines = {}
  for line in (text .. '\n'):gmatch('(.-)\r?\n') do
    table.insert(lines, line)
  end
  return lines
end

--- The file item id of a part (exercise, exam task, summary, …), if the index has one.
local function part_item(ctx, file)
  if ctx.index and file then
    return ctx.index.by_path[file]
  end
  return nil
end

local function part(div, ctx, W, lines)
  local a = div.attributes
  local file = a.file
  if not file or not ctx.file_kind(file) then
    fail(ctx, 'sk-part needs file="<course-relative path>" of a Markdown course file, got ' .. tostring(file))
    return {}
  end
  for _, key in ipairs({ 'hints', 'solution' }) do
    if a[key] and not MODES[a[key]] then
      fail(ctx, 'sk-part ' .. key .. ' must be inline, appendix or none')
      return {}
    end
  end

  ctx.file, ctx.kind = file, ctx.file_kind(file)
  ctx.hint_count = 0
  ctx.hint_mode = a.hints or ctx.solutions
  ctx.solution_mode = a.solution or ctx.solutions
  ctx.part_key, ctx.part_number, ctx.part_title = file, a.number, a.title
  ctx.attach = nil

  local first_line, last_line = (a.lines or ''):match('^(%d+)-(%d+)$')
  if lines and first_line then
    local sub = {}
    for i = tonumber(first_line), math.min(tonumber(last_line), #lines) do
      table.insert(sub, lines[i])
    end
    guard.scan_fences(table.concat(sub, '\n') .. '\n', ctx, tonumber(a.first) or 1)
  end

  local out = pandoc.Blocks({})
  local anchor = solutions.anchor(ctx)
  if anchor then
    out:insert(anchor)
  end
  guard.structure(W.unwrap(div.content), ctx)
  out:extend(keep_intros(W.blocks(div.content, ctx, 'root'), ctx))

  -- generated blocks after the part are not part of the file
  ctx.file, ctx.kind = ctx.doc_file, nil
  ctx.part_key, ctx.part_number, ctx.part_title = nil, nil, nil
  return out
end

---------------------------------------------------------------------------------------
-- Entry point
---------------------------------------------------------------------------------------

local function header(el, ctx, W)
  if el.level > 3 or #el.classes > 0 or #guard.user_attributes(el) > 0 then
    fail(ctx, 'generated headings are levels 1–3 without attributes')
  end
  el.content = W.inlines(el.content, ctx)
  return { el }
end

local function block(el, ctx, W, lines)
  local t = el.t
  if t == 'Header' then
    return header(el, ctx, W)
  elseif t == 'Para' or t == 'Plain' then
    el.content = W.inlines(el.content, ctx)
    return { el }
  elseif t == 'Div' then
    local name = el.classes[1]
    if name == 'sk-part' then
      return part(el, ctx, W, lines)
    elseif name == 'sk-gen' then
      return generator(el, ctx)
    elseif name == 'sk-meta' then
      return { ctx.raw_typst('#sk-meta[\n' .. markup(el.content, ctx, W) .. '\n]') }
    elseif name == 'sk-objectives' then
      return { ctx.raw_typst('#sk-objectives(labels: sk-l)[\n' .. markup(el.content, ctx, W) .. '\n]') }
    elseif name == 'sk-rubric' then
      return rubric(el, ctx, W)
    elseif name == 'sk-answers' then
      return answers(el, ctx, W)
    elseif name == 'sk-unit' then
      local inner = pandoc.Blocks({})
      for _, kid in ipairs(el.content) do
        if kid.t == 'Div' and kid.classes[1] == 'sk-unit' then
          fail(ctx, 'sk-unit blocks do not nest')
        else
          inner:extend(block(kid, ctx, W, lines))
        end
      end
      return { ctx.raw_typst('#sk-unit[\n' .. ctx:typst(inner) .. '\n]') }
    end
    fail(ctx, 'unknown generated block `' .. tostring(name) .. '`')
    return {}
  end
  fail(ctx, 'unexpected ' .. t .. ' at the top level of an assembled document')
  return {}
end

function M.run(doc, ctx, W, source)
  if not KINDS[ctx.doc] then
    fail(ctx, 'unknown sk-doc ' .. ctx.doc)
  end
  ctx.doc_file = ctx.file
  local lines = source and split_lines(source) or nil

  -- Typst labels this document defines, so refs can link inside it: every question and
  -- every part's own item (exercises, exam tasks, summary chapters, …).
  doc:walk({
    Div = function(div)
      if div.classes:includes('mcq') and ctx.label_ok(div.identifier) then
        ctx.labels[div.identifier] = true
      elseif div.classes:includes('sk-part') then
        local id = part_item(ctx, div.attributes.file)
        if id and ctx.label_ok(id) then
          ctx.labels[id] = true
        end
      end
    end,
  })

  local body = pandoc.Blocks({ ctx.raw_typst(solutions.labels(ctx)) })
  for _, el in ipairs(doc.blocks) do
    body:extend(block(el, ctx, W, lines))
  end
  ctx.file, ctx.kind = ctx.doc_file, nil
  body:extend(solutions.appendix(ctx))
  if ctx.doc == 'cheatsheet' then
    body:insert(ctx.raw_typst('#metadata("cs-end") <cs-end>'))
  end

  doc.blocks = body
  if ctx.doc_title then
    doc.meta.title = pandoc.MetaInlines({ pandoc.Str(ctx.doc_title) })
  end
  return doc
end

return M
