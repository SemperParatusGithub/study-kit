-- alttext: readable plain text for a figure's Typst `alt:` (docs/architecture.md §2.3:
-- the caption doubles as alt text). pandoc.utils.stringify would hand a screen reader the
-- TeX source of any math in the caption (`\underline{U}_C`); here Math inlines are read
-- as text instead. The HTML caption keeps the rendered math, so only Typst uses this.
--
--   \underline{U}_C → U_C            \mathrm{k\Omega} → kΩ        3{,}3\,\mathrm{V} → 3,3 V
--   \frac{1}{2\pi R C} → 1/(2πRC)    10^{-3} → 10⁻³               \varphi = 30^\circ → φ = 30°
--
-- Plain Lua apart from the pandoc.Inlines walk in M.inlines, so the TeX part is testable
-- with `pandoc lua`.

local M = {}

local GREEK = {
  alpha = 'α', beta = 'β', gamma = 'γ', delta = 'δ', epsilon = 'ε', varepsilon = 'ε',
  zeta = 'ζ', eta = 'η', theta = 'θ', vartheta = 'ϑ', iota = 'ι', kappa = 'κ',
  lambda = 'λ', mu = 'μ', nu = 'ν', xi = 'ξ', pi = 'π', varpi = 'ϖ', rho = 'ρ',
  varrho = 'ϱ', sigma = 'σ', varsigma = 'ς', tau = 'τ', upsilon = 'υ', phi = 'φ',
  varphi = 'φ', chi = 'χ', psi = 'ψ', omega = 'ω',
  Gamma = 'Γ', Delta = 'Δ', Theta = 'Θ', Lambda = 'Λ', Xi = 'Ξ', Pi = 'Π', Sigma = 'Σ',
  Upsilon = 'Υ', Phi = 'Φ', Psi = 'Ψ', Omega = 'Ω',
}

local SYMBOLS = {
  cdot = '·', times = '×', div = '÷', pm = '±', mp = '∓', ast = '∗', star = '⋆',
  circ = '∘', bullet = '•', approx = '≈', sim = '∼', simeq = '≃', cong = '≅',
  equiv = '≡', propto = '∝', neq = '≠', ne = '≠', le = '≤', leq = '≤', ge = '≥',
  geq = '≥', ll = '≪', gg = '≫', to = '→', rightarrow = '→', leftarrow = '←',
  gets = '←', leftrightarrow = '↔', Rightarrow = '⇒', Leftarrow = '⇐',
  Leftrightarrow = '⇔', iff = '⇔', implies = '⇒', mapsto = '↦', infty = '∞',
  partial = '∂', nabla = '∇', sum = '∑', prod = '∏', int = '∫', oint = '∮',
  degree = '°', ldots = '…', cdots = '⋯', dots = '…', vdots = '⋮',
  lvert = '|', rvert = '|', vert = '|', mid = '|', lVert = '‖', rVert = '‖', Vert = '‖',
  langle = '⟨', rangle = '⟩', lbrace = '{', rbrace = '}', lfloor = '⌊', rfloor = '⌋',
  lceil = '⌈', rceil = '⌉', ['in'] = '∈', notin = '∉', ni = '∋', subset = '⊂',
  subseteq = '⊆', supset = '⊃', cup = '∪', cap = '∩', setminus = '∖',
  emptyset = '∅', varnothing = '∅', forall = '∀', exists = '∃', neg = '¬', land = '∧',
  lor = '∨', oplus = '⊕', otimes = '⊗', perp = '⊥', parallel = '∥', angle = '∠',
  triangle = '△', hbar = 'ℏ', ell = 'ℓ', Re = 'Re', Im = 'Im', prime = '′',
  colon = ':', bot = '⊥', top = '⊤', aleph = 'ℵ',
}

-- \sin x, \lg 2: an operator name between spaces (none before an argument in parentheses).
local FUNCTIONS = {}
for name in (
  'sin cos tan cot sec csc arcsin arccos arctan sinh cosh tanh coth ln log lg exp '
  .. 'max min sup inf lim liminf limsup det dim arg deg gcd ker hom Pr sgn mod bmod'
):gmatch('%S+') do
  FUNCTIONS[name] = true
end

local SPACES = {
  quad = true, qquad = true, enspace = true, thinspace = true, medspace = true,
  thickspace = true, space = true, nobreakspace = true,
}
local IGNORED = {
  left = true, right = true, displaystyle = true, textstyle = true, scriptstyle = true,
  limits = true, nolimits = true, middle = true, negthinspace = true,
  big = true, Big = true, bigg = true, Bigg = true, bigl = true, bigr = true, Bigl = true,
  Bigr = true, biggl = true, biggr = true, Biggl = true, Biggr = true,
}
local TEXT = {
  text = true, textrm = true, textit = true, textbf = true, textup = true, textsf = true,
  texttt = true, textnormal = true, mbox = true,
}
local FONTS = {
  mathrm = true, mathit = true, mathbf = true, mathsf = true, mathtt = true,
  mathcal = true, mathfrak = true, mathscr = true, mathnormal = true, boldsymbol = true,
  bm = true, operatorname = true, underline = true, emph = true,
}
local BLACKBOARD = { R = 'ℝ', N = 'ℕ', Z = 'ℤ', Q = 'ℚ', C = 'ℂ', P = 'ℙ' }
-- Accents become a combining mark on a single character (x̄, ẋ, x⃗), else are dropped.
local ACCENTS = {
  bar = '\u{0304}', overline = '\u{0304}', hat = '\u{0302}', widehat = '\u{0302}',
  tilde = '\u{0303}', widetilde = '\u{0303}', dot = '\u{0307}', ddot = '\u{0308}',
  vec = '\u{20D7}', check = '\u{030C}', breve = '\u{0306}', acute = '\u{0301}',
  grave = '\u{0300}',
}
local CONTROL_SYMBOLS = {
  [','] = ' ', [':'] = ' ', [';'] = ' ', [' '] = ' ', ['>'] = ' ', ['!'] = '',
  ['{'] = '{', ['}'] = '}', ['%'] = '%', ['$'] = '$', ['&'] = '&', ['#'] = '#',
  ['_'] = '_', ['|'] = '‖', ['\\'] = '; ',
}
local SUPERSCRIPT = {
  ['0'] = '⁰', ['1'] = '¹', ['2'] = '²', ['3'] = '³', ['4'] = '⁴', ['5'] = '⁵',
  ['6'] = '⁶', ['7'] = '⁷', ['8'] = '⁸', ['9'] = '⁹', ['+'] = '⁺', ['−'] = '⁻',
  ['='] = '⁼', ['('] = '⁽', [')'] = '⁾', n = 'ⁿ', i = 'ⁱ', T = 'ᵀ',
}
-- Relations and binary operators get a space on each side; − only when binary.
local SPACED = {
  ['='] = true, ['<'] = true, ['>'] = true, ['≈'] = true, ['≠'] = true, ['≤'] = true,
  ['≥'] = true, ['≪'] = true, ['≫'] = true, ['≡'] = true, ['∝'] = true, ['∼'] = true,
  ['≃'] = true, ['≅'] = true, ['→'] = true, ['←'] = true, ['↔'] = true, ['⇒'] = true,
  ['⇐'] = true, ['⇔'] = true, ['↦'] = true, ['∈'] = true, ['∉'] = true, ['+'] = true,
  ['±'] = true, ['∓'] = true, ['×'] = true, ['·'] = true, ['÷'] = true, ['−'] = true,
}
-- After one of these a − is a sign, not a minus.
local OPENS = {
  ['('] = true, ['['] = true, ['{'] = true, ['/'] = true, [','] = true, [';'] = true,
  ['^'] = true, ['_'] = true, ['|'] = true,
}

local UTF8_CHAR = '^[%z\1-\127\194-\244][\128-\191]*'

local function chars(s)
  local out = {}
  for _, cp in utf8.codes(s) do
    out[#out + 1] = utf8.char(cp)
  end
  return out
end

---------------------------------------------------------------------------------------
-- Reading TeX
---------------------------------------------------------------------------------------

local convert -- forward declaration

local function skip_space(p)
  while p.s:sub(p.i, p.i):match('^%s$') do
    p.i = p.i + 1
  end
end

--- The raw TeX of the next argument: a {group}, a control sequence or one character.
local function argument(p)
  skip_space(p)
  local s, i = p.s, p.i
  local c = s:sub(i, i)
  if c == '' then
    return ''
  elseif c == '{' then
    local depth, j = 0, i
    repeat
      local d = s:sub(j, j)
      if d == '\\' then
        j = j + 1
      elseif d == '{' then
        depth = depth + 1
      elseif d == '}' then
        depth = depth - 1
      end
      j = j + 1
    until depth == 0 or j > #s
    p.i = j
    return s:sub(i + 1, j - 2)
  elseif c == '\\' then
    local word = s:match('^\\[A-Za-z]+', i) or s:sub(i, i + 1)
    p.i = i + #word
    return word
  end
  local ch = s:match(UTF8_CHAR, i)
  p.i = i + #ch
  return ch
end

--- An [optional] argument, or nil.
local function optional(p)
  skip_space(p)
  if p.s:sub(p.i, p.i) ~= '[' then
    return nil
  end
  local close = p.s:find(']', p.i, true) or #p.s
  local raw = p.s:sub(p.i + 1, close - 1)
  p.i = close + 1
  return raw
end

--- True for text that reads as one unit after / or √: a number, one symbol (with
--- sub- or superscripts), a √ or differential of such a unit, or something already in
--- parentheses.
local function is_unit(t)
  if t == '' or t:match('^%b()$') or t:match('^[%d.,]+$') then
    return true
  end
  for _, ch in ipairs(chars(t)) do
    if ch:match('^%s$') or SPACED[ch] or ch == '/' then
      return false
    end
  end
  t = t:gsub('^√', '')
  local differential = t:match('^d(.+)$') or t:match('^∂(.+)$')
  if differential and is_unit(differential) then
    return true -- dU/dt, ∂f/∂x
  end
  local rest = t:match('^[%d.,]+(.*)$') or t:gsub(UTF8_CHAR, '', 1)
  if rest == '' or rest:match('^_') then
    return true
  end
  for _, ch in ipairs(chars(rest)) do
    local superscript = false
    for _, sup in pairs(SUPERSCRIPT) do
      superscript = superscript or sup == ch
    end
    if not (superscript or ch == '°' or ch == '′') then
      return false
    end
  end
  return true
end

local function unit(t)
  return is_unit(t) and t or '(' .. t .. ')'
end

local function superscript(t)
  if t == '∘' or t == '°' then
    return '°'
  end
  local out = {}
  for _, ch in ipairs(chars(t)) do
    if ch == '′' then
      out[#out + 1] = ch
    elseif SUPERSCRIPT[ch] then
      out[#out + 1] = SUPERSCRIPT[ch]
    else
      return utf8.len(t) == 1 and '^' .. t or '^(' .. t .. ')'
    end
  end
  return table.concat(out)
end

local function subscript(t)
  return is_unit(t) and '_' .. t or '_(' .. t .. ')'
end

--- Text-mode content of \text{…}: literal, apart from escapes and spacing commands.
local function text_mode(raw)
  return (raw:gsub('\\([,:;!> ])', ' '):gsub('\\([{}%%$&#_])', '%1'):gsub('\\%a+%s*', ''):gsub('[{}]', ''))
end

local function command(name, p)
  if GREEK[name] or SYMBOLS[name] then
    return GREEK[name] or SYMBOLS[name]
  elseif FUNCTIONS[name] then
    skip_space(p)
    return ' ' .. name .. (p.s:sub(p.i, p.i) == '(' and '' or ' ')
  elseif SPACES[name] then
    return ' '
  elseif name == 'left' or name == 'right' then
    skip_space(p)
    if p.s:sub(p.i, p.i) == '.' then
      p.i = p.i + 1 -- \left. and \right. draw nothing
    end
    return ''
  elseif IGNORED[name] then
    return ''
  elseif TEXT[name] then
    return text_mode(argument(p))
  elseif FONTS[name] then
    return convert(argument(p))
  elseif name == 'mathbb' then
    local arg = argument(p)
    return BLACKBOARD[arg] or convert(arg)
  elseif ACCENTS[name] then
    local t = convert(argument(p))
    return utf8.len(t) == 1 and t .. ACCENTS[name] or t
  elseif name == 'frac' or name == 'dfrac' or name == 'tfrac' or name == 'cfrac' then
    local a = convert(argument(p))
    local b = convert(argument(p))
    return unit(a) .. '/' .. unit(b)
  elseif name == 'sqrt' then
    local index = optional(p)
    local t = convert(argument(p))
    return (index and superscript(convert(index)) or '') .. '√' .. unit(t)
  elseif name == 'begin' or name == 'end' then
    argument(p) -- the environment name; rows and columns read as ';' and ' '
    return ' '
  elseif name == 'not' then
    local t = convert(argument(p))
    return t == '=' and '≠' or t == '∈' and '∉' or t
  end
  return name
end

--- Plain text of a TeX fragment, before spacing is tidied.
convert = function(s)
  local p = { s = s, i = 1 }
  local out = {}
  while p.i <= #s do
    local c = s:sub(p.i, p.i)
    if c:match('^%s$') then
      p.i = p.i + 1
    elseif c == '%' then
      local eol = s:find('\n', p.i, true)
      p.i = eol and eol + 1 or #s + 1
    elseif c == '{' then
      local raw = argument(p)
      out[#out + 1] = raw == ',' and ',' or convert(raw) -- {,} is the decimal comma
    elseif c == '}' then
      p.i = p.i + 1
    elseif c == '^' or c == '_' then
      p.i = p.i + 1
      skip_space(p)
      -- a command as the script reads its own arguments: f_\mathrm{g}, A^\mathrm{T}
      local word, t = s:match('^\\[A-Za-z]+', p.i), nil
      if word then
        p.i = p.i + #word
        t = command(word:sub(2), p)
      else
        t = convert(argument(p))
      end
      out[#out + 1] = c == '^' and superscript(t) or subscript(t)
    elseif c == '\\' then
      local word = s:match('^\\[A-Za-z]+', p.i)
      if word then
        p.i = p.i + #word
        out[#out + 1] = command(word:sub(2), p)
      else
        local sym = s:sub(p.i + 1, p.i + 1)
        p.i = p.i + 2
        out[#out + 1] = CONTROL_SYMBOLS[sym] or sym
      end
    elseif c == '&' or c == '~' then
      p.i = p.i + 1
      out[#out + 1] = ' '
    elseif c == '-' then
      p.i = p.i + 1
      out[#out + 1] = '−'
    elseif c == "'" then
      p.i = p.i + 1
      out[#out + 1] = '′'
    elseif c == ',' then
      p.i = p.i + 1
      out[#out + 1] = ', '
    else
      local ch = s:match(UTF8_CHAR, p.i)
      p.i = p.i + #ch
      out[#out + 1] = ch
    end
  end
  return table.concat(out)
end

--- Spaces around relations and binary operators (a − after an opening or an operator
--- is a sign), single spaces, no space before a closing parenthesis or a comma.
local function tidy(s)
  local out, last = {}, nil
  for _, ch in ipairs(chars(s)) do
    if ch:match('^%s$') then
      out[#out + 1] = ' '
    elseif SPACED[ch] and not (ch == '−' and (last == nil or SPACED[last] or OPENS[last])) then
      out[#out + 1] = ' ' .. ch .. ' '
      last = ch
    else
      out[#out + 1] = ch
      last = ch
    end
  end
  local text = table.concat(out):gsub('%s+', ' '):gsub('^ ', ''):gsub(' $', '')
  text = text:gsub('%( ', '('):gsub(' %)', ')'):gsub(' ,', ',')
  return text
end

--- Readable plain text for the TeX source of one formula.
function M.tex(tex)
  return tidy(convert(tex))
end

--- Readable plain text of caption inlines: math is read with M.tex, the rest stringified.
function M.inlines(inlines)
  local readable = pandoc.Inlines(inlines):walk({
    Math = function(el)
      return pandoc.Str(M.tex(el.text))
    end,
  })
  return (pandoc.utils.stringify(readable):gsub('%s+', ' '):gsub('^ ', ''):gsub(' $', ''))
end

return M
