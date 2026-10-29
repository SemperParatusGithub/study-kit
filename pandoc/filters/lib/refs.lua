-- refs: course links resolved against the course index (docs/architecture.md §2.3).
--   [text](ex:<id>)  [text](mc:<id>)  [text](topic:<id>)  [text](exam:<id>)
--   [text](src:<doc>#p=<n>)
-- HTML:  <a class="sk-ref sk-ref-{kind}" href="{route}">text</a>, routes
--          ex     /c/<c>/exercises/<id>/        mc     /c/<c>/mc/<topic>/#<id>
--          topic  /c/<c>/summary/<topic>/       exam   /c/<c>/exams/<exam>/
--          src    /c/<c>/src/<doc>.pdf#page=<n>   (src:<doc> alone: the PDF, no page)
--        mc: links only reach practice-bank questions; exam questions are not linkable.
-- Typst: a link when the target is a label in this document (an exercise or exam task,
--        a question, a summary chapter for topic:), otherwise the text plus
--        „(→ Übung: Titel)“, or the text alone when it is the title.
-- Other links: http(s) and mailto stay as they are; bare URLs and every other target
-- (relative paths, fig: as a link, …) are errors.

local guard = require 'lib.guard'

local M = {}

local KIND_LABEL = { ex = 'ref_ex', mc = 'ref_mc', topic = 'ref_topic', exam = 'ref_exam', src = 'ref_src' }
local ID = '^[a-z0-9][a-z0-9-]*$'
local FIX_SCHEMES = 'link with ex:<id>, mc:<id>, topic:<id>, exam:<id> or src:<doc>#p=<n>'

--- Resolve a course link; returns {route, title, anchor?} or nil after reporting.
function M.resolve(scheme, rest, ctx)
  local function fail(code, message, fix)
    ctx:fail(code, message, fix)
    return nil
  end
  local function missing(code, message, fix)
    ctx:fail_target(code, message, fix)
    return nil
  end
  local idx = ctx:require_index()
  if not idx then
    return nil
  end
  local base = '/c/' .. ctx.course .. '/'

  if scheme == 'src' then
    local doc, frag = rest:match('^([^#]*)#?(.*)$')
    local source = idx.sources[doc]
    if type(source) ~= 'table' then
      return missing('SK-REF-MISSING', 'unknown source document `' .. doc .. '`', 'use a document id from sources/manifest.yaml')
    end
    local page
    if frag ~= '' then
      page = tonumber(frag:match('^p=(%d+)$'))
      if not page then
        return fail('SK-REF-SRC', 'source link `src:' .. rest .. '` has a malformed page', 'write src:' .. doc .. '#p=<page>')
      end
      local pages = tonumber(source.pages)
      pages = pages and (math.tointeger(pages) or pages)
      if page < 1 or (pages and page > pages) then
        return missing(
          'SK-REF-SRC',
          string.format('page %d of `%s` does not exist (%s pages)', page, doc, tostring(pages)),
          'fix the page number'
        )
      end
    end
    local title = type(source.title) == 'string' and source.title or doc
    if page then
      title = title .. ', ' .. ctx:t('page') .. ' ' .. page
    end
    return { route = base .. 'src/' .. doc .. '.pdf' .. (page and ('#page=' .. page) or ''), title = title }
  end

  if not rest:match(ID) then
    return fail('SK-REF-MISSING', 'malformed link target `' .. scheme .. ':' .. rest .. '`', 'write ' .. scheme .. ':<id> with a kebab-case id')
  end
  if scheme == 'topic' then
    local topic = idx.topics[rest]
    if type(topic) ~= 'table' then
      return missing('SK-REF-MISSING', 'unknown topic `' .. rest .. '`', 'use a topic id from course.yaml')
    end
    -- in a PDF that holds the chapter, the link jumps to it (its item is summary-<topic>)
    return { route = base .. 'summary/' .. rest .. '/', title = topic.title or rest, anchor = 'summary-' .. rest }
  elseif scheme == 'exam' then
    local exam = idx.exams[rest]
    if type(exam) ~= 'table' then
      return missing('SK-REF-MISSING', 'unknown exam `' .. rest .. '`', 'use an exam id from exams/<id>/exam.yaml')
    end
    return { route = base .. 'exams/' .. rest .. '/', title = exam.title or rest, anchor = rest }
  end

  local item = idx.items[rest]
  local want = scheme == 'ex' and 'exercise' or 'mc'
  if type(item) ~= 'table' then
    return missing('SK-REF-MISSING', 'unknown ' .. (scheme == 'ex' and 'exercise' or 'question') .. ' `' .. rest .. '`', 'check the id')
  elseif item.kind ~= want then
    return missing(
      'SK-REF-MISSING',
      string.format(
        '`%s:%s` has kind %s, but %s: links need %s',
        scheme,
        rest,
        tostring(item.kind),
        scheme,
        scheme == 'ex' and 'an exercise' or 'a question'
      ),
      'check the id and the prefix'
    )
  end
  local title = item.title or rest
  if scheme == 'ex' then
    return { route = base .. 'exercises/' .. rest .. '/', title = title, anchor = rest }
  end
  local exam = type(item.path) == 'string' and item.path:match('^exams/([^/]+)/') or nil
  if exam then
    local info = idx.exams[exam]
    local exam_title = type(info) == 'table' and type(info.title) == 'string' and info.title or exam
    return missing(
      'SK-REF-MISSING',
      'question `' .. rest .. '` belongs to exam `' .. exam .. '`, not to a practice bank',
      'link the exam instead: [' .. exam_title .. '](exam:' .. exam .. ')'
    )
  end
  if type(item.topic) ~= 'string' then
    return fail('SK-REF-MISSING', 'question `' .. rest .. '` has no topic in the index', 'rebuild the index')
  end
  return { route = base .. 'mc/' .. item.topic .. '/#' .. rest, title = title, anchor = rest }
end

function M.link(el, ctx, W)
  el.content = W.inlines(el.content, ctx)
  if el.identifier ~= '' or #el.classes > 0 or #guard.user_attributes(el) > 0 then
    ctx:fail('SK-REF-LINK', 'links take no attributes', 'remove the {…} after the link')
  end
  local target = el.target
  local scheme, rest = target:match('^([%a][%w+.-]*):(.*)$')
  if scheme == 'http' or scheme == 'https' or scheme == 'mailto' then
    if pandoc.utils.stringify(el.content) == target or target:match('^mailto:') and pandoc.utils.stringify(el.content) == rest then
      ctx:fail('SK-REF-LINK', 'bare URL ' .. target, 'write [descriptive text](' .. target .. ')')
    end
    return { W.clean(el) }
  end
  if not KIND_LABEL[scheme] then
    ctx:fail('SK-REF-SCHEME', 'unsupported link target `' .. target .. '`', FIX_SCHEMES)
    return { W.clean(el) }
  end
  local r = M.resolve(scheme, rest, ctx)
  if not r or ctx.target == 'check' then
    return { W.clean(el) }
  end
  if (scheme == 'ex' or scheme == 'mc') and ctx:quarantined(rest) then
    return el.content -- the target is hidden from the site and the PDFs (§2.10)
  end

  if ctx.target == 'html' then
    local out = pandoc.Inlines({
      pandoc.RawInline(
        'html',
        string.format('<a class="sk-ref sk-ref-%s" href="%s">', scheme, ctx.esc(r.route))
      ),
    })
    out:extend(el.content)
    out:insert(pandoc.RawInline('html', '</a>'))
    return out
  end
  -- Typst
  if r.anchor and ctx.labels[r.anchor] then
    return { pandoc.Link(el.content, '#' .. r.anchor) }
  end
  -- link text that already is the target's title needs no „(→ Thema: …)“ after it
  local function norm(s)
    return (pandoc.text.lower(s):gsub('%s+', ' '):gsub('^ ', ''):gsub(' $', ''))
  end
  if norm(pandoc.utils.stringify(el.content)) == norm(r.title) then
    return el.content
  end
  local out = pandoc.Inlines({})
  out:extend(el.content)
  out:insert(pandoc.Space())
  out:insert(pandoc.Str('(→ ' .. ctx:t(KIND_LABEL[scheme]) .. ': ' .. r.title .. ')'))
  return out
end

--- Bare URLs in running text. `leaves` is an inline list with sourcepos wrappers spliced
--- away ({el, pos} each, from W.leaves). A URL can span several Str elements (+sourcepos
--- splits `https://b.de` at every punctuation mark), so each run of adjacent Strs is
--- joined and searched as one word.
function M.bare_urls(leaves, ctx)
  local i = 1
  while i <= #leaves do
    if leaves[i].el.t ~= 'Str' then
      i = i + 1
    else
      local parts, starts, j, len = {}, {}, i, 0
      while leaves[j] and leaves[j].el.t == 'Str' do
        starts[j] = len + 1
        table.insert(parts, leaves[j].el.text)
        len = len + #leaves[j].el.text
        j = j + 1
      end
      local text = table.concat(parts)
      local at = text:find('https?://') or text:find('%f[%w]www%.[%w-]')
      if at then
        local url = text:sub(at):gsub('[%.,;:!%?%)%]}"\'»“”]+$', '')
        local k = i
        while k + 1 < j and starts[k + 1] <= at do
          k = k + 1
        end
        local href = url:match('^www%.') and ('https://' .. url) or url
        ctx:fail('SK-REF-LINK', 'bare URL ' .. url, 'write [descriptive text](' .. href .. ')', leaves[k].pos)
      end
      i = j
    end
  end
end

return M
