-- meta (HTML only): the last block of every fragment is
--   <script type="application/json" id="sk-meta">
--     {"headings":[{"level":2,"id":"…","text":"…"}],
--      "items":[{"id":"…","kind":"mc|exercise|…","topic":"…","difficulty":n}]}
--   </script>
-- headings: every heading from level 2 down, text as plain text (math as its TeX).
-- items: the file's own index entry (exercise, exam task, summary, …) followed by each MC
-- question in source order; difficulty is null where only the frontmatter knows it.

local M = {}

function M.heading(el, ctx)
  if el.level >= 2 then
    table.insert(ctx.headings, {
      level = el.level,
      id = el.identifier,
      text = pandoc.utils.stringify(el.content),
    })
  end
end

local function nullable(v)
  if v == nil then
    return pandoc.json.null
  end
  return v
end

function M.script(ctx)
  local items = {}
  local id, item = ctx:file_item()
  if id and type(item) == 'table' then
    table.insert(items, {
      id = id,
      kind = nullable(item.kind),
      topic = nullable(item.topic),
      difficulty = pandoc.json.null,
    })
  end
  for _, q in ipairs(ctx.items) do
    table.insert(items, {
      id = q.id,
      kind = q.kind,
      type = nullable(q.type),
      topic = nullable(q.topic),
      difficulty = nullable(q.difficulty),
    })
  end
  local data = { headings = ctx.headings, items = items }
  local json = pandoc.json.encode(data)
  -- An empty Lua table encodes as an object; both lists must stay arrays.
  json = json:gsub('"headings":{}', '"headings":[]'):gsub('"items":{}', '"items":[]')
  json = json:gsub('</', '<\\/')
  return pandoc.RawBlock('html', '<script type="application/json" id="sk-meta">' .. json .. '</script>')
end

return M
