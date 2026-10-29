-- solutions (Typst only): where hints, solutions and MC answer keys go, chosen with
-- -M sk-solutions=inline|appendix|none. In an assembled document (lib/document.lua) each
-- part may choose its own mode for hints and for solutions (ctx.hint_mode,
-- ctx.solution_mode); MC keys follow the solution mode.
--   inline    #sk-hint / #sk-solution in place; sk-mcq shows its key below the question
--   appendix  collected into #sk-appendix sections at the end: one entry per exercise
--             holding all its hints (or its solution) with a back-link to the exercise
--             (label = item id); MC keys get their own section, a summary table first,
--             each entry with a back-link to its question (label = question id)
--   none      dropped (exercise sheets without solutions, exam handouts)
-- Generated rubrics and results (lib/document.lua) attach to the last solution: they
-- follow it inline, join its appendix entry, or are dropped with it.

local M = {}

local function anchor_id(ctx)
  local id = ctx:file_item()
  if id and ctx.label_ok(id) then
    return id
  end
  return nil
end

local function label(ctx, key)
  return '[' .. ctx:typst_inlines({ pandoc.Str(ctx:t(key)) }) .. ']'
end

--- `#let sk-l = (…)`: the label texts the house library prints (typst/studykit.typ).
function M.labels(ctx)
  local keys = {
    { 'yes', 'true' },
    { 'no', 'false' },
    { 'explanation', 'explanation' },
    { 'answer-key', 'answer_key' },
    { 'question', 'question' },
    { 'correct', 'correct' },
    { 'single', 'mc_single' },
    { 'multi', 'mc_multi' },
    { 'kprim', 'mc_kprim' },
    { 'hint', 'hint' },
    { 'solution', 'solution' },
    { 'rubric', 'rubric' },
    { 'criterion', 'criterion' },
    { 'points', 'points' },
    { 'total', 'total' },
    { 'results', 'results' },
    { 'objectives', 'objectives' },
  }
  local parts = {}
  for _, k in ipairs(keys) do
    table.insert(parts, k[1] .. ': ' .. label(ctx, k[2]))
  end
  table.insert(parts, 'page-of: ' .. ctx.typst_str(ctx:t('page_of')))
  return '#let sk-l = (' .. table.concat(parts, ', ') .. ')'
end

--- `#metadata("<id>") <id>`: the anchor appendix entries and in-document links jump to.
function M.anchor(ctx)
  local id = anchor_id(ctx)
  if id and not ctx.anchors[id] then
    ctx.anchors[id] = true
    return ctx.raw_typst(string.format('#metadata(%s) <%s>', ctx.typst_str(id), id))
  end
  return nil
end

--- Blocks for the start of a single-file Typst document: the label texts and the anchor
--- of the file's item, which appendix back-links and in-document links jump to.
function M.preamble(ctx)
  local out = pandoc.Blocks({ ctx.raw_typst(M.labels(ctx)) })
  local anchor = M.anchor(ctx)
  if anchor then
    out:insert(anchor)
  end
  return out
end

--- The appendix title of the current file: "<number> <title>" (the number only in an
--- assembled document), the item title, or `fallback`.
local function entry_title(ctx, fallback)
  local _, item = ctx:file_item()
  local title = ctx.part_title
  if not title and item and type(item.title) == 'string' and item.title ~= '' then
    title = item.title
  end
  title = title or fallback
  if ctx.part_number then
    title = ctx.part_number .. ' ' .. title
  end
  return title
end

--- The hint group of the current file in the appendix (created on first use).
local function hint_group(ctx)
  local key = ctx.part_key or ctx.file
  local group = ctx.appendix.hint_groups[key]
  if not group then
    group = { id = anchor_id(ctx), title = entry_title(ctx, ctx:t('hints')), items = {} }
    ctx.appendix.hint_groups[key] = group
    table.insert(ctx.appendix.hints, group)
  end
  return group
end

function M.hint(ctx, n, body)
  local mode = ctx.hint_mode or ctx.solutions
  local title = ctx:typst_inlines({ pandoc.Str(ctx:t('hint') .. ' ' .. n) })
  if mode == 'inline' then
    return { ctx.raw_typst(string.format('#sk-hint(index: %d, title: [%s])[\n%s\n]', n, title, body)) }
  elseif mode == 'appendix' then
    table.insert(hint_group(ctx).items, string.format('#sk-hint-entry(index: %d, title: [%s])[\n%s\n]', n, title, body))
  end
  return {}
end

function M.solution(ctx, body)
  local mode = ctx.solution_mode or ctx.solutions
  ctx.attach = { mode = mode }
  if mode == 'inline' then
    return {
      ctx.raw_typst(
        string.format('#sk-solution(title: [%s])[\n%s\n]', ctx:typst_inlines({ pandoc.Str(ctx:t('solution')) }), body)
      ),
    }
  elseif mode == 'appendix' then
    local entry = { id = anchor_id(ctx), title = entry_title(ctx, ctx:t('solution')), body = body, extra = {} }
    table.insert(ctx.appendix.solutions, entry)
    ctx.attach.entry = entry
  end
  return {}
end

--- Generated Typst (rubric, results) that belongs to the last solution. Returns the
--- blocks to emit in place: the Typst itself when the solution was inline, else nothing.
function M.attach(ctx, typst)
  local target = ctx.attach or { mode = ctx.solution_mode or ctx.solutions }
  if target.mode == 'inline' then
    return { ctx.raw_typst(typst) }
  elseif target.mode == 'appendix' and target.entry then
    table.insert(target.entry.extra, typst)
  end
  return {}
end

--- An MC answer key: `call` is a complete #sk-mcq-key(…) expression, `row` the
--- (number, id, type, keys) of the summary table.
function M.mcq_key(ctx, call, row)
  if (ctx.solution_mode or ctx.solutions) == 'appendix' then
    table.insert(ctx.appendix.keys, { raw = call, row = row })
  end
end

local function back_arg(ctx, id, key)
  if not id then
    return ''
  end
  return string.format(
    ', back: <%s>, back-label: [%s]',
    id,
    ctx:typst_inlines({ pandoc.Str('↑ ' .. ctx:t(key)) })
  )
end

local function entry(ctx, e, body)
  return string.format(
    '#sk-appendix-entry(title: [%s]%s)[\n%s\n]',
    ctx:typst_inlines({ pandoc.Str(e.title) }),
    back_arg(ctx, e.id, 'back_task'),
    body
  )
end

local function section(ctx, title_key, parts)
  return ctx.raw_typst(
    string.format(
      '#sk-appendix(title: [%s])[\n%s\n]',
      ctx:typst_inlines({ pandoc.Str(ctx:t(title_key)) }),
      table.concat(parts, '\n\n')
    )
  )
end

local function key_table(ctx)
  local rows = {}
  for _, k in ipairs(ctx.appendix.keys) do
    local r = k.row
    local keys = {}
    for _, key in ipairs(r.keys) do
      table.insert(keys, ctx.typst_str(key))
    end
    table.insert(
      rows,
      string.format(
        '(number: %d, id: %s, type: %s, keys: (%s), back: %s),',
        r.number,
        ctx.typst_str(r.id),
        ctx.typst_str(r.type or ''),
        table.concat(keys, ', ') .. (#keys == 1 and ',' or ''),
        ctx.label_ok(r.id) and ('<' .. r.id .. '>') or 'none'
      )
    )
  end
  return '#sk-key-table(labels: sk-l, rows: (\n  ' .. table.concat(rows, '\n  ') .. '\n))'
end

--- Blocks for the end of a Typst document: the appendix sections that have entries.
function M.appendix(ctx)
  local out = pandoc.Blocks({})
  if #ctx.appendix.hints > 0 then
    local parts = {}
    for _, g in ipairs(ctx.appendix.hints) do
      table.insert(parts, entry(ctx, g, table.concat(g.items, '\n\n')))
    end
    out:insert(section(ctx, 'hints', parts))
  end
  if #ctx.appendix.solutions > 0 then
    local parts = {}
    for _, e in ipairs(ctx.appendix.solutions) do
      local body = e.body
      if #e.extra > 0 then
        body = body .. '\n\n' .. table.concat(e.extra, '\n\n')
      end
      table.insert(parts, entry(ctx, e, body))
    end
    out:insert(section(ctx, 'solutions', parts))
  end
  if #ctx.appendix.keys > 0 then
    local parts = { key_table(ctx) }
    for _, k in ipairs(ctx.appendix.keys) do
      table.insert(parts, k.raw)
    end
    out:insert(section(ctx, 'answer_key', parts))
  end
  return out
end

M.back_arg = back_arg

return M
