-- math: the shared math subset (docs/architecture.md §2.3).
--
-- Every Math node is checked against pandoc/math-denylist.json, a JSON array of
--   {"token": "\\tag" | "\\left\\lVert" | "env:vmatrix", "use": "<replacement>",
--    "kind": "silent" | "fails", "unless_wrapped": [["\\left(", "\\right)"], …]?}
-- Tokens are TeX control sequences (a control word never matches a longer word, so \si
-- does not match \sin), sequences of them, or environments written env:<name>.
-- "silent" constructs pass KaTeX and pandoc→Typst but render wrong in the PDF, so only
-- this check stops them. unless_wrapped allows an environment that sits directly between
-- one of the listed \left…\right pairs. Beyond the list: non-ASCII outside \text{…}
-- (KaTeX strict rejects it) and `|` in an array column spec.
--
-- HTML:  <sk-math data-tex="<base64 of the UTF-8 TeX>" data-display="0|1"></sk-math>
-- Typst: each node is converted on its own with pandoc.write, any conversion warning is a
--        finding, then two fixes from Phase 1 apply: digit\,digit (the decimal comma {,})
--        becomes digit","digit, and `quad` follows every column separator in cases(…).
-- json:  the Typst conversion still runs, so the lint fails on what the PDF would fail on.

local M = {}

local denylist -- loaded on first use

---------------------------------------------------------------------------------------
-- TeX tokens
---------------------------------------------------------------------------------------

--- Tokens without whitespace or comments; \begin{x} and \end{x} become begin:x and end:x.
function M.tokenize(tex)
  local toks, i, n = {}, 1, #tex
  while i <= n do
    local c = tex:sub(i, i)
    if c == '\\' then
      local word = tex:match('^\\[A-Za-z]+', i)
      if word then
        i = i + #word
        if word == '\\begin' or word == '\\end' then
          local ws, name = tex:match('^(%s*){([%a*]+)}', i)
          if name then
            table.insert(toks, word:sub(2) .. ':' .. name)
            i = i + #ws + #name + 2
          else
            table.insert(toks, word)
          end
        else
          table.insert(toks, word)
        end
      else
        table.insert(toks, tex:sub(i, i + 1))
        i = i + 2
      end
    elseif c == '%' then
      local eol = tex:find('\n', i, true)
      i = eol and eol + 1 or n + 1
    elseif c:match('%s') then
      i = i + 1
    else
      table.insert(toks, c)
      i = i + 1
    end
  end
  return toks
end

local function token_seq(token)
  local env = token:match('^env:(.+)$')
  if env then
    return { 'begin:' .. env }
  end
  return M.tokenize(token)
end

local function load_denylist(ctx)
  if denylist then
    return denylist
  end
  denylist = {}
  local path = ctx.filter_dir .. '/../math-denylist.json'
  local fh = io.open(path, 'r')
  if not fh then
    ctx:fail('SK-MATH', 'cannot read ' .. path, 'restore pandoc/math-denylist.json')
    return denylist
  end
  local entries = pandoc.json.decode(fh:read('a'), false)
  fh:close()
  for _, e in ipairs(entries) do
    local entry = { token = e.token, use = e.use, kind = e.kind, seq = token_seq(e.token) }
    if type(e.unless_wrapped) == 'table' then
      entry.wrapped = {}
      for _, pair in ipairs(e.unless_wrapped) do
        table.insert(entry.wrapped, { open = M.tokenize(pair[1]), close = M.tokenize(pair[2]) })
      end
    end
    table.insert(denylist, entry)
  end
  return denylist
end

local function seq_at(toks, i, seq)
  for k = 1, #seq do
    if toks[i + k - 1] ~= seq[k] then
      return false
    end
  end
  return true
end

--- Index of the end:<name> that closes begin:<name> at i.
local function matching_end(toks, i)
  local name = toks[i]:sub(7)
  local depth = 0
  for j = i, #toks do
    if toks[j] == 'begin:' .. name then
      depth = depth + 1
    elseif toks[j] == 'end:' .. name then
      depth = depth - 1
      if depth == 0 then
        return j
      end
    end
  end
  return nil
end

local function is_wrapped(toks, i, entry)
  local j = matching_end(toks, i)
  if not j then
    return false
  end
  for _, pair in ipairs(entry.wrapped) do
    if seq_at(toks, i - #pair.open, pair.open) and seq_at(toks, j + 1, pair.close) then
      return true
    end
  end
  return false
end

local TEXT_COMMANDS = {
  ['\\text'] = true,
  ['\\textrm'] = true,
  ['\\textit'] = true,
  ['\\textbf'] = true,
  ['\\textup'] = true,
  ['\\textnormal'] = true,
  ['\\mbox'] = true,
}

--- The first non-ASCII character outside \text{…}, or nil.
local function non_ascii(tex)
  local i, n = 1, #tex
  while i <= n do
    local b = tex:byte(i)
    if b == 92 then -- backslash
      local word = tex:match('^\\[A-Za-z]+', i)
      if not word then
        i = i + 2
      else
        i = i + #word
        if TEXT_COMMANDS[word] then
          local j = i
          while tex:sub(j, j):match('^%s$') do
            j = j + 1
          end
          if tex:sub(j, j) == '{' then
            local depth = 0
            repeat
              local c = tex:sub(j, j)
              if c == '\\' then
                j = j + 1
              elseif c == '{' then
                depth = depth + 1
              elseif c == '}' then
                depth = depth - 1
              end
              j = j + 1
            until depth == 0 or j > n
            i = j
          end
        end
      end
    elseif b >= 128 then
      local ok, cp = pcall(utf8.codepoint, tex, i)
      return ok and utf8.char(cp) or tex:sub(i, i)
    else
      i = i + 1
    end
  end
  return nil
end

local function excerpt(tex)
  local s = tex:gsub('%s+', ' '):gsub('^ ', ''):gsub(' $', '')
  if utf8.len(s) and utf8.len(s) > 60 then
    s = s:sub(1, utf8.offset(s, 58) - 1) .. '…'
  end
  return '$' .. s .. '$'
end

--- Report every denied construct in one formula.
function M.check(tex, ctx)
  local toks = M.tokenize(tex)
  local reported = {}
  for _, entry in ipairs(load_denylist(ctx)) do
    for i = 1, #toks do
      if not reported[entry.token] and seq_at(toks, i, entry.seq) then
        if not (entry.wrapped and is_wrapped(toks, i, entry)) then
          reported[entry.token] = true
          local what = entry.token:match('^env:(.+)$')
          what = what and ('environment ' .. what) or ('`' .. entry.token .. '`')
          ctx:fail('SK-MATH', what .. ' is not allowed in ' .. excerpt(tex), entry.use)
        end
      end
    end
  end
  for i = 1, #toks do
    if toks[i] == 'begin:array' and toks[i + 1] == '{' then
      local j = i + 2
      while toks[j] and toks[j] ~= '}' do
        if toks[j] == '|' then
          ctx:fail('SK-MATH', '`|` in an array column spec in ' .. excerpt(tex), 'a Markdown table')
          break
        end
        j = j + 1
      end
    end
  end
  local ch = non_ascii(tex)
  if ch then
    ctx:fail(
      'SK-MATH',
      'non-ASCII character ' .. ch .. ' outside \\text{…} in ' .. excerpt(tex),
      'put words in \\text{…} and write symbols as TeX commands, e.g. \\Omega'
    )
  end
end

---------------------------------------------------------------------------------------
-- Typst conversion and fix-ups
---------------------------------------------------------------------------------------

--- digit\,digit (pandoc's escaped comma from {,}) → digit","digit.
function M.fix_decimal_comma(s)
  local prev
  repeat
    prev = s
    s = s:gsub('(%d)\\,(%d)', '%1","%2')
  until s == prev
  return s
end

--- Insert `quad` after every column separator directly inside cases(…).
function M.fix_cases(s)
  local out, i, n = {}, 1, #s
  while true do
    local a, b = s:find('%f[%w]cases%(', i)
    if not a then
      table.insert(out, s:sub(i))
      break
    end
    table.insert(out, s:sub(i, b))
    local depth, j, inner = 1, b + 1, {}
    while j <= n do
      local c = s:sub(j, j)
      if c == '"' then
        local k = j + 1
        while k <= n do
          local d = s:sub(k, k)
          if d == '\\' then
            k = k + 2
          elseif d == '"' then
            break
          else
            k = k + 1
          end
        end
        table.insert(inner, s:sub(j, k))
        j = k + 1
      elseif c == '\\' then
        table.insert(inner, s:sub(j, j + 1))
        j = j + 2
      else
        if c == '(' then
          depth = depth + 1
        elseif c == ')' then
          depth = depth - 1
          if depth == 0 then
            break
          end
        end
        if c == '&' and depth == 1 then
          table.insert(inner, '& quad')
        else
          table.insert(inner, c)
        end
        j = j + 1
      end
    end
    -- nested cases(…) inside this one get the same treatment
    table.insert(out, M.fix_cases(table.concat(inner)))
    i = j
  end
  return table.concat(out)
end

local function first_problem(messages)
  for _, msg in ipairs(messages) do
    local ok, data = pcall(function()
      return pandoc.json.decode(pandoc.json.encode(msg), false)
    end)
    if ok and type(data) == 'table' and type(data.message) == 'string' then
      for line in data.message:gmatch('[^\n]+') do
        if line:match('^unexpected') then
          return line
        end
      end
      return (data.message:gsub('\n.*', ''))
    end
  end
  return 'conversion warning'
end

--- Typst markup for one Math node, or nil after reporting a conversion problem.
function M.to_typst(el, ctx)
  local doc = pandoc.Pandoc({ pandoc.Plain({ el }) })
  local messages, out = pandoc.log.silence(pandoc.write, doc, 'typst')
  if #messages > 0 then
    ctx:fail(
      'SK-MATH',
      'pandoc cannot convert ' .. excerpt(el.text) .. ' to Typst: ' .. first_problem(messages),
      'stay within the math subset of docs/architecture.md §2.3'
    )
    return nil
  end
  out = out:gsub('^%s+', ''):gsub('%s+$', '')
  return M.fix_cases(M.fix_decimal_comma(out))
end

---------------------------------------------------------------------------------------
-- HTML
---------------------------------------------------------------------------------------

local B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

function M.base64(s)
  local out = {}
  for i = 1, #s, 3 do
    local a, b, c = s:byte(i, i + 2)
    local v = (a << 16) | ((b or 0) << 8) | (c or 0)
    local chars = {}
    for k = 3, 0, -1 do
      local idx = (v >> (6 * k)) & 63
      table.insert(chars, B64:sub(idx + 1, idx + 1))
    end
    if not b then
      chars[3], chars[4] = '=', '='
    elseif not c then
      chars[4] = '='
    end
    table.insert(out, table.concat(chars))
  end
  return table.concat(out)
end

---------------------------------------------------------------------------------------
-- Entry point for the walker
---------------------------------------------------------------------------------------

function M.inline(el, ctx)
  M.check(el.text, ctx)
  local display = el.mathtype == 'DisplayMath'
  if ctx.target == 'html' then
    return {
      pandoc.RawInline(
        'html',
        string.format('<sk-math data-tex="%s" data-display="%d"></sk-math>', M.base64(el.text), display and 1 or 0)
      ),
    }
  end
  local typ = M.to_typst(el, ctx)
  if ctx.target == 'typst' and typ then
    return { pandoc.RawInline('typst', typ) }
  end
  return { el }
end

return M
