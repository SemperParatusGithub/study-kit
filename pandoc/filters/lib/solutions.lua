-- solutions (Typst only): where hints, solutions and MC answer keys go, chosen with
-- -M sk-solutions=inline|appendix|none.
--   inline    #sk-hint / #sk-solution in place; sk-mcq shows its key below the question
--   appendix  collected into #sk-appendix sections at the end, each entry with a back-link
--             to the exercise (label = item id) or question (label = question id)
--   none      dropped (exercise sheets without solutions, exam handouts)

local M = {}

local function anchor_id(ctx)
  local id = ctx:file_item()
  if id and ctx.label_ok(id) then
    return id
  end
  return nil
end

--- Blocks for the start of a Typst document: label texts for the house library and,
--- in appendix mode, the anchor the appendix links back to.
function M.preamble(ctx)
  local out = pandoc.Blocks({})
  local labels = {
    'yes: [' .. ctx:typst_inlines({ pandoc.Str(ctx:t('true')) }) .. ']',
    'no: [' .. ctx:typst_inlines({ pandoc.Str(ctx:t('false')) }) .. ']',
    'explanation: [' .. ctx:typst_inlines({ pandoc.Str(ctx:t('explanation')) }) .. ']',
    'answer-key: [' .. ctx:typst_inlines({ pandoc.Str(ctx:t('answer_key')) }) .. ']',
  }
  out:insert(ctx.raw_typst('#let sk-l = (' .. table.concat(labels, ', ') .. ')'))
  local id = anchor_id(ctx)
  if ctx.solutions == 'appendix' and id then
    out:insert(ctx.raw_typst(string.format('#metadata(%s) <%s>', ctx.typst_str(id), id)))
  end
  return out
end

function M.hint(ctx, n, body)
  local label = ctx:t('hint') .. ' ' .. n
  if ctx.solutions == 'inline' then
    return {
      ctx.raw_typst(
        string.format('#sk-hint(index: %d, title: [%s])[\n%s\n]', n, ctx:typst_inlines({ pandoc.Str(label) }), body)
      ),
    }
  elseif ctx.solutions == 'appendix' then
    table.insert(ctx.appendix.hints, { title = label, body = body })
  end
  return {}
end

function M.solution(ctx, body)
  if ctx.solutions == 'inline' then
    return {
      ctx.raw_typst(
        string.format('#sk-solution(title: [%s])[\n%s\n]', ctx:typst_inlines({ pandoc.Str(ctx:t('solution')) }), body)
      ),
    }
  elseif ctx.solutions == 'appendix' then
    table.insert(ctx.appendix.solutions, { title = ctx:t('solution'), body = body })
  end
  return {}
end

--- `call` is a complete #sk-mcq-key(...) expression for the appendix.
function M.mcq_key(ctx, call)
  if ctx.solutions == 'appendix' then
    table.insert(ctx.appendix.solutions, { raw = call })
  end
end

local function back_arg(ctx, id, key)
  if not id then
    return ''
  end
  return string.format(
    ', back: <%s>, back-label: [%s]',
    id,
    ctx:typst_inlines({ pandoc.Str('↑ ' .. ctx:t(key)) })
  )
end

local function section(ctx, title_key, entries)
  local id = anchor_id(ctx)
  local parts = {}
  for _, e in ipairs(entries) do
    if e.raw then
      table.insert(parts, e.raw)
    else
      local title = e.title
      local _, item = ctx:file_item()
      if item and type(item.title) == 'string' and item.title ~= '' then
        title = title .. ' – ' .. item.title
      end
      table.insert(
        parts,
        string.format(
          '#sk-appendix-entry(title: [%s]%s)[\n%s\n]',
          ctx:typst_inlines({ pandoc.Str(title) }),
          back_arg(ctx, id, 'back_task'),
          e.body
        )
      )
    end
  end
  return ctx.raw_typst(
    string.format(
      '#sk-appendix(title: [%s])[\n%s\n]',
      ctx:typst_inlines({ pandoc.Str(ctx:t(title_key)) }),
      table.concat(parts, '\n\n')
    )
  )
end

--- Blocks for the end of a Typst document (appendix mode only).
function M.appendix(ctx)
  local out = pandoc.Blocks({})
  if ctx.solutions ~= 'appendix' then
    return out
  end
  if #ctx.appendix.hints > 0 then
    out:insert(section(ctx, 'hints', ctx.appendix.hints))
  end
  if #ctx.appendix.solutions > 0 then
    out:insert(section(ctx, 'solutions', ctx.appendix.solutions))
  end
  return out
end

M.back_arg = back_arg

return M
