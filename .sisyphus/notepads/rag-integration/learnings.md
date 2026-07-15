# Learnings - RAG Integration (Chat UI)

## Completed: Chat.tsx RAG source citations

### Changes made to `frontend/src/pages/Chat.tsx`:

1. **Imports**: Added `DownOutlined` and `PaperClipOutlined` from `@ant-design/icons`.

2. **Message interface**: Added `isRAG?: boolean` field to distinguish RAG answers from regular QA answers.

3. **State additions**:
   - `isRagMode` (boolean) — toggles between `/ai/query` (RAG) and `/qa/ask` (QA) endpoints
   - `expandedSources` (Set of message IDs) — tracks which source sections are expanded

4. **sendMessage() refactored**: Split into RAG mode (calls `/ai/query`) and normal mode (calls `/qa/ask`). RAG mode directly uses the response `{answer, sources}` without needing a separate `/qa/answer` call.

5. **Source citation cards**: Added a collapsible "关于来源" section below AI message content:
   - Shows source count badge
   - Click to expand/collapse with animated chevron
   - Each source card shows: title (bold), content preview (truncated 100 chars), score badge
   - Score badge colors: green (>0.7), orange (>0.5), gray (otherwise)
   - Uses Ant Design Tag with `success`/`warning`/`default` colors

6. **RAG toggle button**: Added next to the send button in the input area. Green gradient when active. Changes label between "RAG问答" and "RAG已开启".

7. **Backward compatibility**: Normal QA flow (/qa/ask) remains completely unchanged.

### Technical notes:
- API base URL is `/api`, so `/ai/query` maps to `/api/ai/query`
- Source rendering uses `line-clamp-2` for content preview (Tailwind)
- `loadSessionMessages` already handles `item.sources` from history — no change needed
