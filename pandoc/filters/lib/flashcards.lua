-- flashcards: the flash cards of a topic's chapter (docs/architecture.md §5.6).
--
-- Source form, in cards/<topic>.md:
--   :::: {.flashcard #card-<topic>-001}
--   Front: a question or a term.
--
--   ::: back
--   The answer.
--   :::
--   ::::
--
-- HTML:  <sk-card data-id data-topic>
--          <div class="sk-card-front">…</div>
--          <div class="sk-card-back">…</div></sk-card>
-- Cards are web only: no PDF document holds them, so Typst output is empty. The card's
-- structure is checked by the Cards stage of `studykit validate`; here only what the
-- renderer needs is reported.

local M = {}

local ID_PATTERN = '^[a-z0-9][a-z0-9-]*$'

local function topic_of(ctx)
  return ctx.file:match('^cards/(.+)%.md$') or ''
end

function M.render(el, ctx, W)
  local id = el.identifier
  if id == '' then
    ctx:fail('SK-CARD-ID', 'flashcard without an id', 'write `:::: {.flashcard #card-<topic>-NNN}`')
  elseif not id:match(ID_PATTERN) then
    ctx:fail('SK-CARD-ID', 'flashcard id `' .. id .. '` is not kebab-case ASCII', 'use e.g. #card-mining-001')
  end
  if #W.guard_attributes(el) > 0 then
    ctx:fail('SK-CARD-ATTR', 'flashcard takes an id and nothing else', 'write `:::: {.flashcard #card-<topic>-NNN}`')
  end

  local front, back = pandoc.Blocks({}), nil
  for _, kid in ipairs(W.unwrap(el.content, ctx.pos)) do
    local b = kid.el
    if b.t == 'Div' and W.guard_div(b, ctx, kid.pos, 'flashcard') == 'back' then
      if back then
        ctx:fail('SK-CARD-BACK', 'flashcard with more than one `::: back`', 'merge them into one block', kid.pos)
      else
        back = W.with_pos(ctx, kid.pos, function()
          return W.blocks(b.content, ctx, 'nested')
        end)
      end
    else
      front:extend(W.with_pos(ctx, kid.pos, function()
        return W.block(b, ctx, 'nested')
      end))
    end
  end
  if not back then
    ctx:fail('SK-CARD-BACK', 'flashcard without `::: back`', 'end the card with one `::: back` block')
  end
  table.insert(ctx.items, { id = id, kind = 'card', topic = topic_of(ctx) })
  if ctx.target ~= 'html' then
    return ctx.target == 'typst' and {} or { el }
  end
  local out = pandoc.Blocks({
    ctx.html(string.format('<sk-card data-id="%s" data-topic="%s">', ctx.esc(id), ctx.esc(topic_of(ctx)))),
    ctx.html('<div class="sk-card-front">'),
  })
  out:extend(front)
  out:insert(ctx.html('</div><div class="sk-card-back">'))
  out:extend(back or {})
  out:insert(ctx.html('</div></sk-card>'))
  return out
end

return M
