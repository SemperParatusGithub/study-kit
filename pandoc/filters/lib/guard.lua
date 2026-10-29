-- guard: the closed list of container blocks and where each may appear
-- (docs/architecture.md §2.3). Fails on unknown classes, misplaced or nested blocks,
-- paragraphs that start with ::: (a fence pandoc did not read as one) and, when the
-- source text is available, on fence lines that are not exactly `::: name`,
-- `:::: {.mcq …}`, `:::` or `::::`. Also rejects raw HTML, which the reader still
-- produces although the dialect turns it off, and `{…}` attributes on anything but an
-- mcq: the HTML writer copies them onto the element, so `onclick` would reach the page.

local M = {}

M.BOXES = { definition = true, theorem = true, example = true, note = true, warning = true, takeaways = true }
local CHEATSHEET_BOXES = { definition = true, note = true, warning = true }
local NAMES = {
  hint = true,
  solution = true,
  definition = true,
  theorem = true,
  example = true,
  note = true,
  warning = true,
  takeaways = true,
  mcq = true,
  explanation = true,
}
local NAME_LIST = 'hint, solution, definition, theorem, example, note, warning, takeaways, mcq, explanation'
local CODE_LANGUAGES = {
  python = true,
  matlab = true,
  octave = true,
  c = true,
  cpp = true,
  vhdl = true,
  verilog = true,
  systemverilog = true,
  julia = true,
  text = true,
}
local SOURCEPOS_KEYS = { ['data-pos'] = true, wrapper = true }

--- Attribute keys an author wrote (sourcepos bookkeeping excluded).
function M.user_attributes(el)
  local keys = {}
  for k, _ in pairs(el.attributes) do
    if not SOURCEPOS_KEYS[k] then
      table.insert(keys, k)
    end
  end
  table.sort(keys)
  return keys
end

local function fence_of(name)
  if name == 'mcq' then
    return '`:::: {.mcq #id type="…" difficulty="…"}`'
  end
  return '`::: ' .. name .. '`'
end

--- Check a container Div; returns its block name, or nil if the class is unknown.
function M.div(el, ctx, parent)
  local classes = el.classes
  if #classes == 0 then
    ctx:fail('SK-BLOCK-UNKNOWN', 'container block without a class', 'open it with `::: name`, name one of: ' .. NAME_LIST)
    return nil
  end
  local name = classes[1]
  if not NAMES[name] then
    ctx:fail('SK-BLOCK-UNKNOWN', 'unknown block class `' .. name .. '`', 'use one of: ' .. NAME_LIST)
    return nil
  end
  if #classes > 1 then
    ctx:fail('SK-BLOCK-FENCE', 'block `' .. name .. '` has more than one class', 'write the fence as ' .. fence_of(name))
  end
  if name ~= 'mcq' and (el.identifier ~= '' or #M.user_attributes(el) > 0) then
    ctx:fail('SK-BLOCK-FENCE', '`' .. name .. '` takes no id or attributes', 'write the fence as ' .. fence_of(name))
  end

  if name == 'explanation' then
    if parent ~= 'mcq' then
      ctx:fail(
        'SK-BLOCK-PLACEMENT',
        '`::: explanation` is only allowed directly inside an mcq',
        'move it to the end of its `:::: {.mcq …}` block'
      )
    end
  elseif parent ~= 'root' then
    ctx:fail(
      'SK-BLOCK-NESTING',
      '`' .. name .. '` cannot be nested in another block or a list',
      'put it at the top level; only `::: explanation` nests, directly inside an mcq'
    )
  end

  local kind = ctx.kind
  if kind then
    if name == 'hint' or name == 'solution' then
      if kind ~= 'exercise' and kind ~= 'exam-task' then
        ctx:fail('SK-BLOCK-PLACEMENT', '`::: ' .. name .. '` is only allowed in exercise and exam task files', 'remove it')
      end
    elseif name == 'mcq' then
      if kind ~= 'mc' then
        ctx:fail('SK-BLOCK-PLACEMENT', 'mcq blocks are only allowed in mc/<topic>.md and exams/<exam>/mc.md', 'move the question')
      end
    elseif M.BOXES[name] then
      if kind == 'cheatsheet' then
        if not CHEATSHEET_BOXES[name] then
          ctx:fail(
            'SK-BLOCK-PLACEMENT',
            '`::: ' .. name .. '` is not allowed in the cheat sheet',
            'use definition, note or warning, or plain text'
          )
        end
      elseif kind ~= 'summary' then
        ctx:fail('SK-BLOCK-PLACEMENT', '`::: ' .. name .. '` is only allowed in summary chapters', 'use plain text here')
      end
    end
  end
  return name
end

--- A paragraph with a line that starts with ::: is a fence pandoc did not read as one.
function M.para(el, ctx, W)
  local inls = W.flatten(el.content)
  local i = 1
  while i <= #inls do
    -- +sourcepos splits ":::" into one Str per character, so join the leading Strs.
    local j, text = i, ''
    while inls[j] and inls[j].t == 'Str' do
      text = text .. inls[j].text
      j = j + 1
    end
    if text:sub(1, 3) == ':::' then
      ctx:fail(
        'SK-BLOCK-FENCE',
        'malformed fence `' .. text .. '` in a paragraph',
        'fences are `::: name` or `:::` alone on a line, with a blank line before the block and after it'
      )
      return
    end
    -- continue at the start of the next line
    i = j
    while inls[i] and inls[i].t ~= 'SoftBreak' and inls[i].t ~= 'LineBreak' do
      i = i + 1
    end
    i = i + 1
  end
end

function M.header(el, ctx)
  if el.level == 1 then
    ctx:fail('SK-BLOCK-MARKDOWN', 'H1 headings are not allowed in the body', 'the title comes from the frontmatter; start at ##')
  end
  if #el.classes > 0 or #M.user_attributes(el) > 0 then
    ctx:fail('SK-BLOCK-MARKDOWN', 'heading attributes are not allowed', 'remove the {…} after the heading')
  end
end

function M.code(el, ctx)
  local lang = el.classes[1]
  if #el.classes ~= 1 or not CODE_LANGUAGES[lang] or #M.user_attributes(el) > 0 then
    ctx:fail(
      'SK-BLOCK-CODE',
      'code blocks need exactly one language and no attributes',
      'fence it as ```python (or matlab, octave, c, cpp, vhdl, verilog, systemverilog, julia, text)'
    )
  end
end

function M.note(_, ctx)
  ctx:fail('SK-BLOCK-MARKDOWN', 'footnotes are not allowed', 'say it in the text or in a `::: note` box')
end

--- Raw HTML from the reader. commonmark_x keeps raw_html even with -raw_html (pandoc
--- 3.13), so the dialect's "no raw HTML" rule is enforced here, on every target; the
--- element is dropped. The walker never revisits the raw elements the modules emit.
function M.raw(el, ctx)
  local excerpt = el.text:gsub('%s+', ' '):gsub('^ ', ''):gsub(' $', '')
  if utf8.len(excerpt) and utf8.len(excerpt) > 40 then
    excerpt = excerpt:sub(1, utf8.offset(excerpt, 38) - 1) .. '…'
  end
  local what = el.format == 'html' and 'raw HTML' or ('raw ' .. el.format)
  ctx:fail('SK-BLOCK-RAW', what .. ' `' .. excerpt .. '` is not allowed', 'use Markdown, math or a container block')
end

--- True if an author wrote an id, a class or an attribute on `el`.
local function has_attributes(el)
  return el.identifier ~= '' or #el.classes > 0 or #M.user_attributes(el) > 0
end

function M.span(el, ctx)
  if has_attributes(el) then
    ctx:fail('SK-BLOCK-MARKDOWN', 'spans with attributes are not allowed', 'remove the {…} after the bracketed text')
  end
end

--- Inline code is written as is: an attribute such as `onclick` would reach the page.
function M.inline_code(el, ctx)
  if has_attributes(el) then
    ctx:fail('SK-BLOCK-MARKDOWN', 'inline code takes no attributes', 'remove the {…} after the code span')
  end
end

--- A `{…}` line above a pipe table puts its attributes on the <table>.
function M.table(el, ctx)
  if has_attributes(el) then
    ctx:fail('SK-BLOCK-MARKDOWN', 'tables take no attributes', 'remove the {…} line above the table')
  end
end

--- File-level rules for exercises and exam tasks: 1–3 hints, exactly one solution, last.
function M.structure(root, ctx)
  if ctx.kind ~= 'exercise' and ctx.kind ~= 'exam-task' then
    return
  end
  local hints, solutions = {}, {}
  for i, entry in ipairs(root) do
    local el = entry.el
    if el.t == 'Div' and el.classes[1] == 'hint' then
      table.insert(hints, entry)
    elseif el.t == 'Div' and el.classes[1] == 'solution' then
      table.insert(solutions, { pos = entry.pos, last = i == #root })
    end
  end
  if #solutions == 0 then
    ctx:fail('SK-BLOCK-SOLUTION', 'missing `::: solution`', 'end the file with exactly one `::: solution` block', '0:0')
  elseif #solutions > 1 then
    ctx:fail('SK-BLOCK-SOLUTION', 'more than one `::: solution`', 'merge them into one block', solutions[2].pos)
  end
  for _, s in ipairs(solutions) do
    if not s.last then
      ctx:fail('SK-BLOCK-SOLUTION', '`::: solution` must be the last block', 'move everything after it above it', s.pos)
    end
  end
  if #hints == 0 then
    ctx:fail('SK-BLOCK-HINTS', 'missing `::: hint`', 'add 1–3 hints: principle, set-up, key intermediate result', '0:0')
  elseif #hints > 3 then
    ctx:fail('SK-BLOCK-HINTS', string.format('%d hints, at most 3 are allowed', #hints), 'merge or drop hints', hints[4].pos)
  end
end

---------------------------------------------------------------------------------------
-- Fence lines. The AST cannot tell `:::` from `::::`, so this scans the source text.
---------------------------------------------------------------------------------------

local function split_lines(text)
  local lines = {}
  for line in (text .. '\n'):gmatch('(.-)\r?\n') do
    table.insert(lines, line)
  end
  if lines[#lines] == '' then
    table.remove(lines)
  end
  return lines
end

--- Check the fence lines of `text`. `first` is the file line of its first line (default 1;
--- an assembled PDF document scans each part with the line its body starts on).
function M.scan_fences(text, ctx, first)
  local lines = split_lines(text)
  local offset = (first or 1) - 1
  local function blank(i)
    return i < 1 or i > #lines or lines[i]:match('^%s*$') ~= nil
  end
  local function fence(i)
    return i >= 1 and i <= #lines and lines[i]:match('^%s*:::') ~= nil
  end
  local function fail(i, message, fix, code)
    ctx:fail(code or 'SK-BLOCK-FENCE', message, fix, (i + offset) .. ':1')
  end

  local stack = {}
  local code = nil -- open code fence: {char = '`', len = 3}
  for i, line in ipairs(lines) do
    if code then
      local run = line:match('^%s*(' .. code.char .. '+)%s*$')
      if run and #run >= code.len then
        code = nil
      end
    else
      local run = line:match('^%s*(```+)') or line:match('^%s*(~~~+)')
      if run then
        code = { char = run:sub(1, 1), len = #run }
      elseif fence(i) then
        local colons, rest = line:match('^(:+)(.*)$')
        if not colons then
          fail(i, 'fence does not start in column 1', 'remove the indentation')
        else
          rest = rest:gsub('%s+$', '')
          if rest == '' then
            local top = stack[#stack]
            if not top then
              fail(i, 'closing fence without an open block', 'remove it or open the block')
            else
              if #colons ~= top.len then
                fail(
                  i,
                  string.format('closing fence has %d colons, `%s` opened with %d', #colons, top.name, top.len),
                  'close with ' .. string.rep(':', top.len)
                )
              end
              table.remove(stack)
              if not (blank(i + 1) or fence(i + 1)) then
                fail(i, 'no blank line after the closing fence', 'add an empty line after it', 'SK-BLOCK-BLANK')
              end
            end
          else
            local name = rest:match('^ ([%w-]+)$')
            if not name and rest:match('^ {%.mcq[%s}]') then
              name = 'mcq'
            end
            if not name then
              fail(
                i,
                'malformed fence `' .. line .. '`',
                'write `::: name` or `:::: {.mcq #id type="…" difficulty="…"}`'
              )
            else
              local want = name == 'mcq' and 4 or 3
              if #colons ~= want then
                fail(
                  i,
                  string.format('`%s` fence has %d colons, it needs exactly %d', name, #colons, want),
                  'write ' .. fence_of(name)
                )
              end
              if not (blank(i - 1) or fence(i - 1)) then
                fail(i, 'no blank line before the fence', 'add an empty line before it', 'SK-BLOCK-BLANK')
              end
              table.insert(stack, { name = name, len = #colons, line = i })
            end
          end
        end
      end
    end
  end
  for _, open in ipairs(stack) do
    fail(open.line, '`' .. open.name .. '` is never closed', 'close it with ' .. string.rep(':', open.len))
  end
end

return M
