-- figures: `![Caption, doubles as alt text](fig:<slug>)` alone in its paragraph
-- (docs/architecture.md §2.3). The slug must be in the course index (index.figures).
--   HTML   <figure class="sk-fig" data-slug="{slug}"><div class="sk-fig-slot"></div>
--          <figcaption>{caption}</figcaption></figure>   (the site inlines the SVG)
--   Typst  #figure(image("<figdir>/<slug>.svg", alt: "…"), caption: […])
-- Typst resolves absolute paths against --root, so a figure directory inside pandoc's
-- working directory (the repository root, which is also the Typst root) is written
-- relative to it: /courses/<c>/_build/figures/<slug>.svg.

local guard = require 'lib.guard'

local M = {}

local SLUG = '^[a-z0-9][a-z0-9-]*$'
local FIX_ALONE = 'put ![Caption](fig:<slug>) alone in its paragraph, with blank lines around it'

local function typst_dir(ctx)
  local dir = ctx.figdir
  if not dir then
    if not ctx.reported_no_figdir then
      ctx.reported_no_figdir = true
      ctx:fail('SK-FIG', 'Typst output needs the figure directory (-M sk-figdir)', 'run pandoc through studykit.pandoc')
    end
    return nil
  end
  dir = dir:gsub('/+$', '')
  local cwd = pandoc.system.get_working_directory()
  if dir:sub(1, #cwd + 1) == cwd .. '/' then
    return dir:sub(#cwd + 1)
  end
  return dir
end

--- An image that is the only element of its paragraph.
function M.block(img, ctx, W)
  local src = img.src
  local slug = src:match('^fig:(.*)$')
  if not slug then
    ctx:fail('SK-FIG', 'only figure images are allowed, found `' .. src .. '`', 'write figures/<slug>.py and use ![Caption](fig:<slug>)')
    return { pandoc.Para({ img }) }
  end
  if img.identifier ~= '' or #img.classes > 0 or #guard.user_attributes(img) > 0 or img.title ~= '' then
    ctx:fail('SK-FIG', 'figure `' .. slug .. '` has attributes or a title', 'write just ![Caption](fig:' .. slug .. ')')
  end
  if not slug:match(SLUG) then
    ctx:fail('SK-FIG', 'figure slug `' .. slug .. '` is not kebab-case ASCII', 'rename the figure script')
  elseif ctx:require_index() and not ctx.index.figure_set[slug] then
    ctx:fail('SK-FIG', 'unknown figure `' .. slug .. '`', 'add figures/' .. slug .. '.py or fix the slug')
  end
  if #W.flatten(img.caption) == 0 then
    ctx:fail('SK-FIG', 'figure `' .. slug .. '` has no caption', 'write ![Caption, doubles as alt text](fig:' .. slug .. ')')
  end
  local caption = W.inlines(img.caption, ctx)

  if ctx.target == 'html' then
    return {
      ctx.html(
        string.format(
          '<figure class="sk-fig" data-slug="%s"><div class="sk-fig-slot"></div><figcaption>',
          ctx.esc(slug)
        )
      ),
      pandoc.Plain(caption),
      ctx.html('</figcaption></figure>'),
    }
  elseif ctx.target == 'typst' then
    local dir = typst_dir(ctx)
    if not dir then
      return {}
    end
    return {
      ctx.raw_typst(
        string.format(
          '#figure(image(%s, alt: %s), caption: [%s])',
          ctx.typst_str(dir .. '/' .. slug .. '.svg'),
          ctx.typst_str(pandoc.utils.stringify(img.caption)),
          ctx:typst_inlines(caption)
        )
      ),
    }
  end
  return { pandoc.Para({ img }) }
end

--- An image inside running text: never allowed.
function M.inline(img, ctx, W)
  if img.src:match('^fig:') then
    ctx:fail('SK-FIG', 'figure `' .. img.src:sub(5) .. '` is not alone in its paragraph', FIX_ALONE)
  else
    ctx:fail('SK-FIG', 'only figure images are allowed, found `' .. img.src .. '`', 'write figures/<slug>.py and use ![Caption](fig:<slug>)')
  end
  img.caption = W.inlines(img.caption, ctx)
  return { img }
end

return M
