-- blocks: container blocks (docs/architecture.md §2.3, §3.1).
--   HTML   <aside class="sk-block sk-{name}" data-block="{name}">
--            <div class="sk-block-title">{title}</div> … </aside>
--          <details class="sk-hint" data-index="{n}"><summary>Hinweis n</summary> … </details>
--          <details class="sk-solution"><summary>Lösung</summary> … </details>
--   Typst  #sk-box(kind: "{name}", title: [{title}])[…]; hints and solutions go through
--          solutions.lua (inline, appendix or none).
-- If the first child of a box is a paragraph made of one bold span, it becomes the title;
-- otherwise the title is the localised block name.

local solutions = require 'lib.solutions'

local M = {}

--- Split off a title paragraph: returns title inlines (or nil) and the remaining blocks.
local function split_title(el, W)
  if #el.content == 0 then
    return nil, el.content, nil
  end
  -- Look through sourcepos wrappers, but keep them on the remaining blocks.
  local first = W.unwrap({ el.content[1] })
  if #first == 1 and (first[1].el.t == 'Para' or first[1].el.t == 'Plain') then
    local flat = W.flatten(first[1].el.content)
    if #flat == 1 and flat[1].t == 'Strong' then
      local rest = pandoc.Blocks({})
      for i = 2, #el.content do
        rest:insert(el.content[i])
      end
      return flat[1].content, rest, first[1].pos
    end
  end
  return nil, el.content, nil
end

function M.box(name, el, ctx, W)
  local title_inlines, body, title_pos = split_title(el, W)
  local title
  if title_inlines then
    title = W.with_pos(ctx, title_pos, function()
      return W.inlines(title_inlines, ctx)
    end)
  else
    title = pandoc.Inlines({ pandoc.Str(ctx:t(name)) })
  end
  body = W.blocks(body, ctx, 'nested')

  if ctx.target == 'html' then
    local out = pandoc.Blocks({
      ctx.html(
        string.format(
          '<aside class="sk-block sk-%s" data-block="%s"><div class="sk-block-title">',
          ctx.esc(name),
          ctx.esc(name)
        )
      ),
      pandoc.Plain(title),
      ctx.html('</div>'),
    })
    out:extend(body)
    out:insert(ctx.html('</aside>'))
    return out
  elseif ctx.target == 'typst' then
    return {
      ctx.raw_typst(
        string.format(
          '#sk-box(kind: %s, title: [%s])[\n%s\n]',
          ctx.typst_str(name),
          ctx:typst_inlines(title),
          ctx:typst(body)
        )
      ),
    }
  end
  return { el }
end

--- `::: hint` and `::: solution` (exercises and exam tasks only; guard checks that).
function M.exercise_block(name, el, ctx, W)
  local body = W.blocks(el.content, ctx, 'nested')
  local n
  if name == 'hint' then
    ctx.hint_count = ctx.hint_count + 1
    n = ctx.hint_count
  end

  if ctx.target == 'html' then
    local open
    if name == 'hint' then
      open = string.format(
        '<details class="sk-hint" data-index="%d"><summary>%s %d</summary>',
        n,
        ctx.esc(ctx:t('hint')),
        n
      )
    else
      open = string.format('<details class="sk-solution"><summary>%s</summary>', ctx.esc(ctx:t('solution')))
    end
    local out = pandoc.Blocks({ ctx.html(open) })
    out:extend(body)
    out:insert(ctx.html('</details>'))
    return out
  elseif ctx.target == 'typst' then
    if name == 'hint' then
      return solutions.hint(ctx, n, ctx:typst(body))
    end
    return solutions.solution(ctx, ctx:typst(body))
  end
  return { el }
end

return M
