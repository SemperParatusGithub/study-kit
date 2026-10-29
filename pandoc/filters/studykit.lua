-- study-kit pandoc filter: one entry point for every target (docs/architecture.md §3.1).
--
-- FORMAT decides what happens:
--   html*   the website contract: <aside>/<details> blocks, <sk-mc>, <sk-math>, sk-meta
--   typst   calls into the house library typst/studykit.typ
--   other   (json, native, …) validation only; the AST is returned unchanged
--
-- Metadata, all plain strings passed with -M (build the argv with studykit.pandoc):
--   sk-index      absolute path of courses/<c>/_build/index.json
--   sk-course     course id
--   sk-lang       de | en
--   sk-file       course-relative path of the source file; decides the file kind
--   sk-solutions  typst only: inline | appendix | none (default appendix)
--   sk-figdir     typst only: absolute directory of the built figures
--   sk-scope      course (default) | file: with file, link and figure targets missing
--                 from the index are not reported (the quick lint of one edited file)
--
-- Findings are collected over the whole document and printed to stderr, one per line,
--   <sk-file>:<line>:<col> SK-CODE message (fix: …)
-- then pandoc exits with status 65. Line and column come from +sourcepos (the json lint
-- run); without it they are 0:0. When pandoc reads a file (not stdin), guard.lua also
-- scans its fence lines, which the AST cannot show.

local script_dir = (PANDOC_SCRIPT_FILE or ''):match('^(.*)[/\\]') or '.'
package.path = script_dir .. '/?.lua;' .. package.path

-- Module names are prefixed with lib. so `math` cannot shadow Lua's math library.
local i18n = require 'lib.i18n'
local guard = require 'lib.guard'
local blocks = require 'lib.blocks'
local mcq = require 'lib.mcq'
local skmath = require 'lib.math'
local figures = require 'lib.figures'
local refs = require 'lib.refs'
local meta = require 'lib.meta'
local solutions = require 'lib.solutions'

local EXIT_FINDINGS = 65

---------------------------------------------------------------------------------------
-- Context: everything the modules share for one document.
---------------------------------------------------------------------------------------

local Ctx = {}
Ctx.__index = Ctx

local function meta_string(m, key)
  local value = m[key]
  if value == nil then
    return nil
  end
  local s = pandoc.utils.stringify(value)
  if s == '' then
    return nil
  end
  return s
end

local function target_of(format)
  if format:match('^html') then
    return 'html'
  elseif format == 'typst' then
    return 'typst'
  end
  return 'check'
end

--- File kind from the course-relative path (docs/architecture.md §2.1).
local function file_kind(rel)
  if rel == 'overview.md' then
    return 'overview'
  elseif rel == 'cheatsheet.md' then
    return 'cheatsheet'
  elseif rel:match('^summary/[^/]+%.md$') then
    return 'summary'
  elseif rel:match('^exercises/[^/]+/[^/]+%.md$') then
    return 'exercise'
  elseif rel:match('^mc/[^/]+%.md$') or rel:match('^exams/[^/]+/mc%.md$') then
    return 'mc'
  elseif rel:match('^exams/[^/]+/[^/]+%.md$') then
    return 'exam-task'
  end
  return nil
end

function Ctx.new(doc)
  local m = doc.meta
  local self = setmetatable({}, Ctx)
  self.filter_dir = script_dir
  self.target = target_of(FORMAT)
  self.file = meta_string(m, 'sk-file')
  self.course = meta_string(m, 'sk-course')
  self.lang = meta_string(m, 'sk-lang')
  self.index_path = meta_string(m, 'sk-index')
  self.figdir = meta_string(m, 'sk-figdir')
  self.solutions = meta_string(m, 'sk-solutions') or 'appendix'
  self.scope = meta_string(m, 'sk-scope') or 'course'
  self.pos = nil
  self.errors = {}
  self.seen_errors = {}
  self.headings = {}
  self.items = {}
  self.hint_count = 0
  self.question_count = 0
  self.labels = {} -- Typst labels defined in this document (for in-document refs)
  self.appendix = { hints = {}, solutions = {} }

  if not self.file then
    self.file = '<stdin>'
    self:fail('SK-PANDOC-FAIL', 'missing -M sk-file', 'run pandoc through studykit.pandoc, which passes it')
  else
    self.kind = file_kind(self.file)
    if not self.kind then
      self:fail(
        'SK-STRUCT-PATH',
        'cannot tell the file kind of ' .. self.file,
        'pass the course-relative path, e.g. summary/03-rc-filter.md or mc/rc-filter.md'
      )
    end
  end
  if self.index_path then
    self:load_index()
  end
  self.course = self.course or (self.index and self.index.course) or 'course'
  self.lang = self.lang or (self.index and self.index.lang) or 'de'
  if not i18n.languages[self.lang] then
    self:fail('SK-PANDOC-FAIL', 'unsupported language ' .. self.lang, 'set course.lang to de or en')
    self.lang = 'en'
  end
  if self.scope ~= 'course' and self.scope ~= 'file' then
    self:fail('SK-PANDOC-FAIL', 'sk-scope must be course or file', 'fix the pandoc argv')
    self.scope = 'course'
  end
  if not ({ inline = true, appendix = true, none = true })[self.solutions] then
    self:fail('SK-PANDOC-FAIL', 'sk-solutions must be inline, appendix or none', 'fix the pandoc argv')
    self.solutions = 'appendix'
  end
  return self
end

function Ctx:load_index()
  local fh = io.open(self.index_path, 'r')
  if not fh then
    self:fail('SK-PANDOC-FAIL', 'cannot read the course index ' .. self.index_path, 'run `studykit index <course> --json`')
    return
  end
  local text = fh:read('a')
  fh:close()
  local ok, data = pcall(pandoc.json.decode, text, false)
  if not ok or type(data) ~= 'table' or data.schema ~= 1 then
    self:fail('SK-PANDOC-FAIL', 'course index is not schema 1 JSON: ' .. self.index_path, 'rebuild it with `studykit index`')
    return
  end
  for _, key in ipairs({ 'topics', 'items', 'exams', 'sources', 'figures' }) do
    if type(data[key]) ~= 'table' then
      data[key] = {}
    end
  end
  data.figure_set = {}
  for _, slug in ipairs(data.figures) do
    data.figure_set[slug] = true
  end
  data.by_path = {} -- one item per file; MC banks hold many questions and have none
  for id, item in pairs(data.items) do
    if type(item) == 'table' and type(item.path) == 'string' and item.kind ~= 'mc' then
      data.by_path[item.path] = id
    end
  end
  self.index = data
end

--- The index, or nil after reporting (once) that it is missing.
function Ctx:require_index()
  if self.index then
    return self.index
  end
  if not self.index_path and not self.reported_no_index then
    self.reported_no_index = true
    self:fail('SK-PANDOC-FAIL', 'references need the course index (-M sk-index)', 'run pandoc through studykit.pandoc')
  end
  return nil
end

--- The index entry for this file (exercise, exam task, summary, …), if any.
function Ctx:file_item()
  if self.index and self.file then
    local id = self.index.by_path[self.file]
    if id then
      return id, self.index.items[id]
    end
  end
  return nil, nil
end

function Ctx:t(key)
  return i18n.t(self.lang, key)
end

--- Record a finding about a target that depends on other files (an id the index lacks).
--- With sk-scope=file the target may simply not be written yet, so it is not reported.
function Ctx:fail_target(code, message, fix)
  if self.scope == 'course' then
    self:fail(code, message, fix)
  end
end

--- Record a finding. `pos` defaults to the innermost source position seen so far.
function Ctx:fail(code, message, fix, pos)
  local where = pos or self.pos or '0:0'
  local text = string.format('%s:%s %s %s', self.file or '<stdin>', where, code, message)
  if fix then
    text = text .. ' (fix: ' .. fix .. ')'
  end
  if not self.seen_errors[text] then
    self.seen_errors[text] = true
    local line, col = where:match('^(%d+):(%d+)$')
    table.insert(self.errors, { line = tonumber(line) or 0, col = tonumber(col) or 0, n = #self.errors, text = text })
  end
end

function Ctx:report_and_exit()
  if #self.errors == 0 then
    return
  end
  table.sort(self.errors, function(a, b)
    if a.line ~= b.line then
      return a.line < b.line
    elseif a.col ~= b.col then
      return a.col < b.col
    end
    return a.n < b.n
  end)
  for _, e in ipairs(self.errors) do
    io.stderr:write(e.text, '\n')
  end
  io.stderr:flush()
  os.exit(EXIT_FINDINGS)
end

-- HTML ------------------------------------------------------------------------------

local HTML_ESCAPES = { ['&'] = '&amp;', ['<'] = '&lt;', ['>'] = '&gt;', ['"'] = '&quot;' }

function Ctx.esc(s)
  return (tostring(s):gsub('[&<>"]', HTML_ESCAPES))
end

function Ctx.html(s)
  return pandoc.RawBlock('html', s)
end

-- Typst -----------------------------------------------------------------------------

--- Typst markup for a list of blocks (already processed by the walker).
function Ctx:typst(blks)
  local out = pandoc.write(pandoc.Pandoc(blks), 'typst')
  return (out:gsub('^%s+', ''):gsub('%s+$', ''))
end

function Ctx:typst_inlines(inls)
  return self:typst({ pandoc.Plain(inls) })
end

--- A Typst string literal.
function Ctx.typst_str(s)
  return '"' .. tostring(s):gsub('[\\"]', '\\%0'):gsub('\n', '\\n') .. '"'
end

--- True if `id` can be written as a Typst label <id>.
function Ctx.label_ok(id)
  return type(id) == 'string' and id:match('^[%w][%w_.:-]*$') ~= nil
end

--- A raw Typst block; the trailing newline keeps a blank line before the next block.
function Ctx.raw_typst(s)
  return pandoc.RawBlock('typst', s .. '\n')
end

---------------------------------------------------------------------------------------
-- Walker: one recursive pass that tracks source positions and dispatches to modules.
-- +sourcepos wraps blocks in Div and inlines in Span elements marked wrapper="1" with a
-- data-pos attribute; the walker splices them away and keeps the position in ctx.pos.
---------------------------------------------------------------------------------------

local W = {}

local BLOCK_ATTR = { Div = true, Header = true, CodeBlock = true, Table = true, Figure = true }
local INLINE_ATTR = { Span = true, Link = true, Image = true, Code = true }

--- "line:col" from an element's data-pos attribute ("file@l:c-l:c" or "l:c-l:c").
function W.pos_of(el)
  if not (BLOCK_ATTR[el.t] or INLINE_ATTR[el.t]) then
    return nil
  end
  local dp = el.attributes['data-pos']
  if not dp then
    return nil
  end
  dp = dp:match('@([^@]*)$') or dp
  local line, col = dp:match('^(%d+):(%d+)')
  if line then
    return line .. ':' .. col
  end
  return nil
end

function W.is_wrapper(el)
  return (el.t == 'Div' or el.t == 'Span') and el.attributes['wrapper'] == '1'
end

--- Drop the sourcepos attribute from an element that is kept.
function W.clean(el)
  if (BLOCK_ATTR[el.t] or INLINE_ATTR[el.t]) and el.attributes['data-pos'] then
    el.attributes['data-pos'] = nil
  end
  return el
end

--- Blocks with wrapper Divs spliced away: a list of {el = block, pos = "l:c" | nil}.
function W.unwrap(blks, pos, out)
  out = out or {}
  for _, el in ipairs(blks) do
    local p = W.pos_of(el) or pos
    if W.is_wrapper(el) then
      W.unwrap(el.content, p, out)
    else
      table.insert(out, { el = el, pos = p })
    end
  end
  return out
end

--- Inlines with wrapper Spans spliced away: a list of {el = inline, pos = "l:c" | nil}.
function W.leaves(inls, pos, out)
  out = out or {}
  for _, el in ipairs(inls) do
    local p = W.pos_of(el) or pos
    if W.is_wrapper(el) then
      W.leaves(el.content, p, out)
    else
      table.insert(out, { el = el, pos = p })
    end
  end
  return out
end

--- Inlines with wrapper Spans spliced away (recursively).
function W.flatten(inls)
  local out = pandoc.Inlines({})
  for _, el in ipairs(inls) do
    if W.is_wrapper(el) then
      out:extend(W.flatten(el.content))
    else
      out:insert(el)
    end
  end
  return out
end

function W.with_pos(ctx, p, fn)
  local saved = ctx.pos
  if p then
    ctx.pos = p
  end
  local result = fn()
  ctx.pos = saved
  return result
end

local function walk_inlines(inls, ctx)
  local out = pandoc.Inlines({})
  for _, el in ipairs(inls) do
    W.with_pos(ctx, W.pos_of(el), function()
      if W.is_wrapper(el) then
        out:extend(walk_inlines(el.content, ctx))
      else
        out:extend(W.inline(el, ctx))
      end
    end)
  end
  return out
end

--- Walk an inline list. Text checks that span several Str elements (+sourcepos splits
--- words at punctuation) run here on the list as a whole.
function W.inlines(inls, ctx)
  refs.bare_urls(W.leaves(inls), ctx)
  return walk_inlines(inls, ctx)
end

function W.inline(el, ctx)
  local t = el.t
  if t == 'Math' then
    return skmath.inline(el, ctx)
  elseif t == 'Link' then
    return refs.link(el, ctx, W)
  elseif t == 'Image' then
    return figures.inline(el, ctx, W)
  elseif t == 'Note' then
    guard.note(el, ctx)
    return {}
  elseif t == 'Str' then
    return { el }
  elseif t == 'Span' then
    guard.span(el, ctx)
    el.content = W.inlines(el.content, ctx)
    return { W.clean(el) }
  elseif t == 'Code' then
    guard.inline_code(el, ctx)
    return { W.clean(el) }
  elseif t == 'RawInline' then
    guard.raw(el, ctx)
    return {}
  elseif el.content ~= nil and t ~= 'Cite' then
    -- Emph, Strong, Underline, Strikeout, Superscript, Subscript, SmallCaps, Quoted
    el.content = W.inlines(el.content, ctx)
    return { el }
  end
  return { el }
end

--- Walk a block list. `parent` is 'root', 'mcq' or 'nested' (lists, boxes, tables, …).
function W.blocks(blks, ctx, parent)
  local out = pandoc.Blocks({})
  for _, el in ipairs(blks) do
    W.with_pos(ctx, W.pos_of(el), function()
      if W.is_wrapper(el) then
        out:extend(W.blocks(el.content, ctx, parent))
      else
        out:extend(W.block(el, ctx, parent))
      end
    end)
  end
  return out
end

--- guard.div for a Div directly inside an mcq.
function W.guard_div(el, ctx, pos)
  return W.with_pos(ctx, pos, function()
    return guard.div(el, ctx, 'mcq')
  end)
end

--- Walk nested block and inline lists of an element we do not handle specially
--- (lists, block quotes, tables, definition lists, line blocks).
function W.generic(el, ctx)
  return el:walk({
    traverse = 'topdown',
    Blocks = function(blks)
      return W.blocks(blks, ctx, 'nested'), false
    end,
    Inlines = function(inls)
      return W.inlines(inls, ctx), false
    end,
  })
end

function W.block(el, ctx, parent)
  local t = el.t
  if t == 'Div' then
    local name = guard.div(el, ctx, parent)
    if name == 'mcq' then
      return mcq.render(el, ctx, W)
    elseif name == 'hint' or name == 'solution' then
      return blocks.exercise_block(name, el, ctx, W)
    elseif name and guard.BOXES[name] then
      return blocks.box(name, el, ctx, W)
    end
    -- unknown class or a stray explanation: already reported; keep the content
    return W.blocks(el.content, ctx, 'nested')
  elseif t == 'Para' or t == 'Plain' then
    guard.para(el, ctx, W)
    local flat = W.flatten(el.content)
    if #flat == 1 and flat[1].t == 'Image' then
      return W.with_pos(ctx, W.pos_of(el.content[1]), function()
        return figures.block(flat[1], ctx, W)
      end)
    end
    el.content = W.inlines(el.content, ctx)
    return { el }
  elseif t == 'Header' then
    guard.header(el, ctx)
    meta.heading(el, ctx)
    el.content = W.inlines(el.content, ctx)
    return { W.clean(el) }
  elseif t == 'CodeBlock' then
    guard.code(el, ctx)
    return { W.clean(el) }
  elseif t == 'RawBlock' then
    guard.raw(el, ctx)
    return {}
  elseif t == 'HorizontalRule' then
    return { el }
  elseif t == 'Table' then
    guard.table(el, ctx)
  end
  return { W.clean(W.generic(el, ctx)) }
end

---------------------------------------------------------------------------------------
-- Entry point
---------------------------------------------------------------------------------------

local function read_source()
  local files = PANDOC_STATE.input_files or {}
  if #files ~= 1 or files[1] == '-' then
    return nil
  end
  local fh = io.open(files[1], 'r')
  if not fh then
    return nil
  end
  local text = fh:read('a')
  fh:close()
  return text
end

function Pandoc(doc)
  local ctx = Ctx.new(doc)

  local source = read_source()
  if source then
    guard.scan_fences(source, ctx)
  end

  -- Typst labels this document defines, so refs can link inside it.
  doc:walk({
    Div = function(div)
      if div.classes:includes('mcq') and Ctx.label_ok(div.identifier) then
        ctx.labels[div.identifier] = true
      end
    end,
  })
  local file_id = ctx:file_item()
  if file_id and Ctx.label_ok(file_id) then
    ctx.labels[file_id] = true
  end

  -- The walker edits elements in place; validation runs keep the AST as authored.
  local blks = ctx.target == 'check' and doc:clone().blocks or doc.blocks
  guard.structure(W.unwrap(blks), ctx)
  local body = W.blocks(blks, ctx, 'root')

  if ctx.target == 'html' then
    body:insert(meta.script(ctx))
  elseif ctx.target == 'typst' then
    local head = solutions.preamble(ctx)
    head:extend(body)
    head:extend(solutions.appendix(ctx))
    body = head
  end

  ctx:report_and_exit()
  if ctx.target == 'check' then
    return doc
  end
  doc.blocks = body
  return doc
end
