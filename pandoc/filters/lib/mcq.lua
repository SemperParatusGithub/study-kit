-- mcq: multiple-choice questions (docs/architecture.md §2.6).
--
-- Source form:
--   :::: {.mcq #mc-rc-filter-003 type="single" difficulty="1"}
--   Stem …
--
--   - [x] option text
--
--     why paragraph
--
--   - [ ] …
--
--   ::: explanation
--   …
--   :::
--   ::::
--
-- pandoc 3.13 keeps task-list markers in loose lists: every item is
-- [Para [Str "☒"|"☐", Space, …], Para why] (checked in tests/py/test_filters.py).
--
-- HTML:  <sk-mc data-id data-type data-difficulty data-topic data-pin-last>
--          <div class="sk-stem">…</div>
--          <sk-opt data-key="A" data-correct="true"><div class="sk-opt-text">…</div>
--            <div class="sk-why" hidden>…</div></sk-opt> …
--          <div class="sk-explanation" hidden>…</div></sk-mc>
--        Options stay in source order; the site shuffles at runtime.
-- Typst: #sk-mcq(id:, number:, type:, difficulty:, answers:, options: ((key:, text:,
--        correct:, why:), …), explanation:, labels: sk-l)[stem] <id>, options in a
--        deterministic shuffle seeded by the question id (pin-last keeps the last option
--        last), keys (A)–(F) assigned after shuffling; numbers run through the whole
--        document; the answer key goes through solutions.lua.

local solutions = require 'lib.solutions'

local M = {}

local COUNTS = { single = { 3, 5 }, multi = { 4, 6 }, kprim = { 4, 4 } }
local ATTRS = { type = true, difficulty = true, tags = true, source = true, ['pin-last'] = true }
local SOURCEPOS_KEYS = { ['data-pos'] = true, wrapper = true }
local CHECKED, UNCHECKED = '☒', '☐'
local KEYS = 'ABCDEFGHIJ'
local ID_PATTERN = '^[a-z0-9][a-z0-9-]*$'

-- Options that make every other option pointless (lower-case substrings).
local ALL_OF_THE_ABOVE = {
  'all of the above',
  'all the above',
  'alle oben',
  'alle obigen',
  'alle genannten',
  'alle aussagen sind richtig',
  'alle antworten sind richtig',
}
-- Words that refer to an option by its letter, which shuffling breaks.
local LETTER_WORDS = {
  option = true,
  antwort = true,
  answer = true,
  aussage = true,
  statement = true,
  choice = true,
}

---------------------------------------------------------------------------------------
-- Deterministic shuffle: FNV-1a 32-bit hash of the id seeds mulberry32, then
-- Fisher-Yates from the end (j = floor(rand() * i) for i = n … 2, 1-based).
---------------------------------------------------------------------------------------

local U32 = 0xffffffff

local function fnv1a(s)
  local h = 0x811c9dc5
  for i = 1, #s do
    h = ((h ~ s:byte(i)) * 0x01000193) & U32
  end
  return h
end

local function mulberry32(seed)
  local a = seed & U32
  return function()
    a = (a + 0x6D2B79F5) & U32
    local t = a
    t = ((t ~ (t >> 15)) * (t | 1)) & U32
    t = (t ~ ((t + (((t ~ (t >> 7)) * (t | 61)) & U32)) & U32)) & U32
    return ((t ~ (t >> 14)) & U32) / 4294967296
  end
end

--- Display order (list of source indices) for n options.
function M.order(id, n, pin_last)
  local order = {}
  for i = 1, n do
    order[i] = i
  end
  local rand = mulberry32(fnv1a(id))
  local last = pin_last and n - 1 or n
  for i = last, 2, -1 do
    local j = math.floor(rand() * i) + 1
    order[i], order[j] = order[j], order[i]
  end
  return order
end

---------------------------------------------------------------------------------------
-- Parsing and validation
---------------------------------------------------------------------------------------

local function lower_text(inls)
  return pandoc.text.lower(pandoc.utils.stringify(inls))
end

local function parse_option(label, index, item, ctx, W, list_pos)
  local parts = W.unwrap(item, list_pos)
  local first = parts[1]
  local opt = { pos = first and first.pos or list_pos, index = index }
  local function fail(code, message, fix)
    ctx:fail(code, label .. ': ' .. message, fix, opt.pos)
  end
  if not first or (first.el.t ~= 'Para' and first.el.t ~= 'Plain') then
    fail('SK-MCQ-FORMAT', string.format('option %d is not a task item', index), 'start it with `- [ ] ` or `- [x] `')
    return nil
  end
  local inl = first.el.content
  local box = inl[1]
  if not (box and box.t == 'Str' and (box.text == CHECKED or box.text == UNCHECKED)) then
    fail('SK-MCQ-FORMAT', string.format('option %d is not a task item', index), 'start it with `- [ ] ` or `- [x] `')
    return nil
  end
  opt.correct = box.text == CHECKED
  local skip = (inl[2] and inl[2].t == 'Space') and 2 or 1
  opt.text = pandoc.Inlines({})
  for i = skip + 1, #inl do
    opt.text:insert(inl[i])
  end
  if #W.flatten(opt.text) == 0 then
    fail('SK-MCQ-FORMAT', string.format('option %d has no text', index), 'write the option after the checkbox')
  end
  if #parts < 2 then
    fail(
      'SK-MCQ-WHY',
      string.format('option %d has no why paragraph', index),
      'add an indented paragraph after a blank line: why it is right, or which mistake it models'
    )
  elseif #parts > 2 or parts[2].el.t ~= 'Para' then
    fail(
      'SK-MCQ-WHY',
      string.format('option %d must have exactly two paragraphs (option text, why)', index),
      'keep one why paragraph per option'
    )
  else
    opt.why = parts[2]
  end
  local text = lower_text(opt.text)
  for _, phrase in ipairs(ALL_OF_THE_ABOVE) do
    if text:find(phrase, 1, true) then
      fail('SK-MCQ-ALL-ABOVE', '"all of the above" options are not allowed', 'write a real distractor or a "none of these" option')
      break
    end
  end
  return opt
end

--- Parse and validate an mcq Div; returns the question table (fields may be missing
--- after errors, which are reported through ctx).
function M.parse(el, ctx, W)
  local q = { id = el.identifier, pos = ctx.pos, options = {}, stem = pandoc.Blocks({}) }
  local function fail(code, message, fix, pos)
    ctx:fail(code, message, fix, pos or q.pos)
  end
  local label = q.id ~= '' and q.id or 'mcq'

  if q.id == '' then
    fail('SK-MCQ-ATTR', 'mcq without an id', 'write `:::: {.mcq #mc-<topic>-NNN type="single" difficulty="2"}`')
  elseif not q.id:match(ID_PATTERN) then
    fail('SK-MCQ-ATTR', 'mcq id `' .. q.id .. '` is not kebab-case ASCII', 'use e.g. #mc-rc-filter-003')
  end

  local attrs = {}
  for k, v in pairs(el.attributes) do
    if not SOURCEPOS_KEYS[k] then
      if ATTRS[k] then
        attrs[k] = v
      else
        fail('SK-MCQ-ATTR', label .. ': unknown attribute `' .. k .. '`', 'allowed: type, difficulty, tags, source, pin-last')
      end
    end
  end
  q.type = attrs.type
  if not COUNTS[q.type] then
    fail('SK-MCQ-ATTR', label .. ': type must be single, multi or kprim', 'add type="single", type="multi" or type="kprim"')
  end
  if not (attrs.difficulty and attrs.difficulty:match('^[1-4]$')) then
    fail('SK-MCQ-ATTR', label .. ': difficulty must be 1, 2, 3 or 4', 'add difficulty="2"')
  else
    q.difficulty = tonumber(attrs.difficulty)
  end
  local pin = attrs['pin-last']
  if pin ~= nil and pin ~= 'true' and pin ~= 'false' then
    fail('SK-MCQ-ATTR', label .. ': pin-last must be "true" or "false"', 'write pin-last="true"')
  end
  q.pin_last = pin == 'true'
  q.tags = attrs.tags
  q.source = attrs.source

  -- pandoc ends a task list at an item without a checkbox and starts a new one, so the
  -- options may arrive as several consecutive lists.
  local lists, explanation, after_options = {}, nil, false
  for _, kid in ipairs(W.unwrap(el.content, q.pos)) do
    local b = kid.el
    if b.t == 'BulletList' then
      if explanation then
        fail('SK-MCQ-FORMAT', label .. ': options after the explanation', 'put the explanation last', kid.pos)
      elseif after_options then
        fail('SK-MCQ-FORMAT', label .. ': options must form one list', 'remove what separates the options', kid.pos)
      else
        table.insert(lists, kid)
      end
    else
      after_options = #lists > 0
      if b.t == 'Div' then
        local name = W.guard_div(b, ctx, kid.pos)
        if name == 'explanation' then
          if explanation then
            fail('SK-MCQ-EXPLANATION', label .. ': more than one explanation', 'merge them into one `::: explanation`', kid.pos)
          elseif #lists == 0 then
            fail('SK-MCQ-FORMAT', label .. ': the explanation must come after the options', 'move it to the end', kid.pos)
          end
          explanation = explanation or kid
        end
      elseif b.t == 'OrderedList' then
        fail('SK-MCQ-FORMAT', label .. ': options must be a task list', 'write each option as `- [ ] …` or `- [x] …`', kid.pos)
      elseif #lists > 0 or explanation then
        fail(
          'SK-MCQ-FORMAT',
          label .. ': unexpected block after the options',
          'the stem comes first, then the options, then the explanation',
          kid.pos
        )
      else
        q.stem:insert(b)
        q.stem_pos = q.stem_pos or kid.pos
      end
    end
  end

  if #q.stem == 0 then
    fail('SK-MCQ-FORMAT', label .. ': no question stem', 'write the question before the options')
  end
  if not explanation then
    fail('SK-MCQ-EXPLANATION', label .. ': missing `::: explanation`', 'end the question with one `::: explanation` block')
  else
    q.explanation = explanation
    for _, word, letter in pandoc.utils.stringify(explanation.el.content):gmatch('()(%a+)%s+%(?([A-F])%)?%f[^%w]') do
      if LETTER_WORDS[pandoc.text.lower(word)] then
        fail(
          'SK-MCQ-LETTER',
          label .. ': the explanation refers to option ' .. letter .. ' by its letter',
          'options are shuffled; name the option by its content',
          explanation.pos
        )
        break
      end
    end
  end
  if #lists == 0 then
    fail('SK-MCQ-COUNT', label .. ': no option list', 'add options as `- [x] …` / `- [ ] …`, each with a why paragraph')
    return q
  end

  local count = 0
  for _, list in ipairs(lists) do
    for _, item in ipairs(list.el.content) do
      count = count + 1
      local opt = parse_option(label, count, item, ctx, W, list.pos)
      if opt then
        table.insert(q.options, opt)
      end
    end
  end
  if #q.options ~= count then
    return q -- option errors already reported; counts would only add noise
  end

  local range = COUNTS[q.type]
  if range then
    local n, correct = #q.options, 0
    for _, o in ipairs(q.options) do
      if o.correct then
        correct = correct + 1
      end
    end
    if n < range[1] or n > range[2] then
      local want = range[1] == range[2] and tostring(range[1]) or (range[1] .. '–' .. range[2])
      fail('SK-MCQ-COUNT', string.format('%s: %s needs %s options, found %d', label, q.type, want, n), 'add or remove options')
    end
    if q.type == 'single' and correct ~= 1 then
      fail(
        'SK-MCQ-KEY',
        string.format('%s: single needs exactly one [x], found %d', label, correct),
        'mark exactly one option `- [x]`, or use type="multi"'
      )
    elseif q.type == 'multi' and (correct == 0 or correct == n) then
      fail(
        'SK-MCQ-KEY',
        string.format('%s: multi needs at least one [x] and at least one [ ], found %d of %d', label, correct, n),
        'mark the correct options with [x] and keep at least one wrong option'
      )
    end
  end
  return q
end

---------------------------------------------------------------------------------------
-- Rendering
---------------------------------------------------------------------------------------

local function topic_of(q, ctx)
  local item = ctx.index and ctx.index.items[q.id]
  if type(item) == 'table' and type(item.topic) == 'string' then
    return item.topic
  end
  return ctx.file and ctx.file:match('^mc/([^/]+)%.md$') or ''
end

--- Walk the parts of a parsed question once (math, refs, figures inside them).
local function walk_parts(q, ctx, W)
  q.stem_out = W.with_pos(ctx, q.stem_pos, function()
    return W.blocks(q.stem, ctx, 'nested')
  end)
  for _, o in ipairs(q.options) do
    W.with_pos(ctx, o.pos, function()
      o.text_out = W.blocks({ pandoc.Plain(o.text) }, ctx, 'nested')
    end)
    if o.why then
      o.why_out = W.blocks({ o.why.el }, ctx, 'nested')
    end
  end
  if q.explanation then
    q.explanation_out = W.with_pos(ctx, q.explanation.pos, function()
      return W.blocks(q.explanation.el.content, ctx, 'explanation')
    end)
  end
end

local function render_html(q, ctx)
  local esc = ctx.esc
  local out = pandoc.Blocks({
    ctx.html(
      string.format(
        '<sk-mc data-id="%s" data-type="%s" data-difficulty="%s" data-topic="%s" data-pin-last="%s"%s%s>',
        esc(q.id),
        esc(q.type or ''),
        esc(q.difficulty or ''),
        esc(topic_of(q, ctx)),
        q.pin_last and 'true' or 'false',
        q.tags and string.format(' data-tags="%s"', esc(q.tags)) or '',
        q.source and string.format(' data-source="%s"', esc(q.source)) or ''
      )
    ),
    ctx.html('<div class="sk-stem">'),
  })
  out:extend(q.stem_out)
  out:insert(ctx.html('</div>'))
  for i, o in ipairs(q.options) do
    out:insert(
      ctx.html(
        string.format(
          '<sk-opt data-key="%s" data-correct="%s"><div class="sk-opt-text">',
          KEYS:sub(i, i),
          o.correct and 'true' or 'false'
        )
      )
    )
    out:extend(o.text_out)
    out:insert(ctx.html('</div><div class="sk-why" hidden>'))
    out:extend(o.why_out or {})
    out:insert(ctx.html('</div></sk-opt>'))
  end
  out:insert(ctx.html('<div class="sk-explanation" hidden>'))
  out:extend(q.explanation_out or {})
  out:insert(ctx.html('</div>'))
  out:insert(ctx.html('</sk-mc>'))
  return out
end

local function typst_options(q, ctx)
  local order = M.order(q.id, #q.options, q.pin_last)
  local parts, keys = {}, {}
  for pos, src in ipairs(order) do
    local o = q.options[src]
    if o.correct then
      table.insert(keys, KEYS:sub(pos, pos))
    end
    table.insert(
      parts,
      string.format(
        '(key: "%s", text: [%s], correct: %s, why: [%s]),',
        KEYS:sub(pos, pos),
        ctx:typst(o.text_out),
        o.correct and 'true' or 'false',
        ctx:typst(o.why_out or {})
      )
    )
  end
  return '(\n    ' .. table.concat(parts, '\n    ') .. '\n  )', keys
end

local function render_typst(q, ctx)
  local options, keys = typst_options(q, ctx)
  local explanation = ctx:typst(q.explanation_out or {})
  local id = ctx.label_ok(q.id) and q.id or nil
  local mode = ctx.solution_mode or ctx.solutions
  ctx.question_count = ctx.question_count + 1
  local number = ctx.question_count
  local call = string.format(
    '#sk-mcq(\n  id: %s,\n  number: %d,\n  type: %s,\n  difficulty: %s,\n  answers: %s,\n  options: %s,\n  explanation: [%s],\n  labels: sk-l,\n)[\n%s\n]%s',
    ctx.typst_str(q.id),
    number,
    ctx.typst_str(q.type or ''),
    q.difficulty and tostring(q.difficulty) or 'none',
    ctx.typst_str(mode),
    options,
    explanation,
    ctx:typst(q.stem_out),
    id and (' <' .. id .. '>') or ''
  )
  if mode == 'appendix' then
    solutions.mcq_key(
      ctx,
      string.format(
        '#sk-mcq-key(\n  id: %s,\n  type: %s,\n  title: [%s],\n  options: %s,\n  explanation: [%s],\n  labels: sk-l%s,\n)',
        ctx.typst_str(q.id),
        ctx.typst_str(q.type or ''),
        ctx:typst_inlines({ pandoc.Str(ctx:t('question') .. ' ' .. number) }),
        options,
        explanation,
        solutions.back_arg(ctx, id, 'back_question')
      ),
      { number = number, id = q.id, type = q.type, keys = keys }
    )
  end
  return { ctx.raw_typst(call) }
end

function M.render(el, ctx, W)
  local q = M.parse(el, ctx, W)
  walk_parts(q, ctx, W)
  if ctx:quarantined(q.id) then
    return {} -- checked above, but hidden from the site and the PDFs (§2.10)
  end
  table.insert(ctx.items, {
    id = q.id,
    kind = 'mc',
    type = q.type,
    topic = topic_of(q, ctx),
    difficulty = q.difficulty,
  })
  if ctx.target == 'html' then
    return render_html(q, ctx)
  elseif ctx.target == 'typst' then
    return render_typst(q, ctx)
  end
  return { el }
end

return M
