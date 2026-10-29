-- refs: course links resolved against the course index (docs/architecture.md §2.3).
--   [text](ex:<id>)  [text](mc:<id>)  [text](topic:<id>)  [text](exam:<id>)
--   [text](src:<doc>#p=<n>)
-- HTML:  <a class="sk-ref sk-ref-{kind}" href="{route}">text</a>, routes
--          ex     /c/<c>/exercises/<id>/        mc     /c/<c>/mc/<topic>/#<id>
--          topic  /c/<c>/summary/<topic>/       exam   /c/<c>/exams/<exam>/
--          src    /c/<c>/src/<doc>.pdf#page=<n>
--        (an mc question from exams/<exam>/mc.md links to /c/<c>/exams/<exam>/#<id>)
-- Typst: a link when the target is a label in this document, otherwise the text plus
--        „(→ Übung: Titel)“.
-- Other links: http(s) and mailto stay as they are; bare URLs and every other target
-- (relative paths, fig: as a link, …) are errors.

local guard = require 'lib.guard'

local M = {}

local KIND_LABEL = { ex = 'ref_ex', mc = 'ref_mc', topic = 'ref_topic', exam = 'ref_exam', src = 'ref_src' }
local ID = '^[a-z0-9][a-z0-9-]*$'
local FIX_SCHEMES = 'link with ex:<id>, mc:<id>, topic:<id>, exam:<id> or src:<doc>#p=<n>'

--- Resolve a course link; returns {route, title, anchor?} or nil after reporting.
function M.resolve(scheme, rest, ctx)
  local function fail(message, fix)
    ctx:fail('SK-REF', message, fix)
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
      return fail('unknown source document `' .. doc .. '`', 'use a document id from sources/manifest.yaml')
    end
    local page
    if frag ~= '' then
      page = tonumber(frag:match('^p=(%d+)$'))
      if not page then
        return fail('source link `src:' .. rest .. '` has a malformed page', 'write src:' .. doc .. '#p=<page>')
      end
      local pages = tonumber(source.pages)
      pages = pages and (math.tointeger(pages) or pages)
      if page < 1 or (pages and page > pages) then
        return fail(
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
    return fail('malformed link target `' .. scheme .. ':' .. rest .. '`', 'write ' .. scheme .. ':<id> with a kebab-case id')
  end
  if scheme == 'topic' then
    local topic = idx.topics[rest]
    if type(topic) ~= 'table' then
      return fail('unknown topic `' .. rest .. '`', 'use a topic id from course.yaml')
    end
    return { route = base .. 'summary/' .. rest .. '/', title = topic.title or rest }
  elseif scheme == 'exam' then
    local exam = idx.exams[rest]
    if type(exam) ~= 'table' then
      return fail('unknown exam `' .. rest .. '`', 'use an exam id from exams/<id>/exam.yaml')
    end
    return { route = base .. 'exams/' .. rest .. '/', title = exam.title or rest, anchor = rest }
  end

  local item = idx.items[rest]
  local want = scheme == 'ex' and 'exercise' or 'mc'
  if type(item) ~= 'table' then
    return fail('unknown ' .. (scheme == 'ex' and 'exercise' or 'question') .. ' `' .. rest .. '`', 'check the id')
  elseif item.kind ~= want then
    return fail(
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
    return { route = base .. 'exams/' .. exam .. '/#' .. rest, title = title, anchor = rest }
  end
  if type(item.topic) ~= 'string' then
    return fail('question `' .. rest .. '` has no topic in the index', 'rebuild the index')
  end
  return { route = base .. 'mc/' .. item.topic .. '/#' .. rest, title = title, anchor = rest }
end

function M.link(el, ctx, W)
  el.content = W.inlines(el.content, ctx)
  if el.identifier ~= '' or #el.classes > 0 or #guard.user_attributes(el) > 0 then
    ctx:fail('SK-REF', 'links take no attributes', 'remove the {…} after the link')
  end
  local target = el.target
  local scheme, rest = target:match('^([%a][%w+.-]*):(.*)$')
  if scheme == 'http' or scheme == 'https' or scheme == 'mailto' then
    if pandoc.utils.stringify(el.content) == target or target:match('^mailto:') and pandoc.utils.stringify(el.content) == rest then
      ctx:fail('SK-REF', 'bare URL ' .. target, 'write [descriptive text](' .. target .. ')')
    end
    return { W.clean(el) }
  end
  if not KIND_LABEL[scheme] then
    ctx:fail('SK-REF', 'unsupported link target `' .. target .. '`', FIX_SCHEMES)
    return { W.clean(el) }
  end
  local r = M.resolve(scheme, rest, ctx)
  if not r or ctx.target == 'check' then
    return { W.clean(el) }
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
  local out = pandoc.Inlines({})
  out:extend(el.content)
  out:insert(pandoc.Space())
  out:insert(pandoc.Str('(→ ' .. ctx:t(KIND_LABEL[scheme]) .. ': ' .. r.title .. ')'))
  return out
end

--- Bare URLs in running text.
function M.str(el, ctx)
  if el.text:match('^https?://') or el.text:match('^www%.') then
    ctx:fail('SK-REF', 'bare URL ' .. el.text, 'write [descriptive text](' .. el.text .. ')')
  end
end

return M
