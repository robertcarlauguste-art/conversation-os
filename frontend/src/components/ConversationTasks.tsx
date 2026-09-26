"use client";

import { useState } from "react";
import type { ActionItemOut } from "@/lib/types";
import { MemoryItemEditor } from "./MemoryItemEditor";

export function ConversationTasks({ memoryId, items }: { memoryId: string; items: ActionItemOut[] }) {
  const [filter, setFilter] = useState("open");
  const completed = items.filter(item => item.status === "COMPLETED").length;
  const shown = items.filter(item => filter === "all" || (item.status === "COMPLETED") === (filter === "completed"));
  return <>
    <p className="mb-3 text-sm">{items.length - completed} open · {completed} completed</p>
    <label className="mb-3 block text-sm">Show tasks
      <select value={filter} onChange={event => setFilter(event.target.value)} className="mt-1 block w-full rounded border border-line bg-paper p-2">
        <option value="open">Open</option><option value="completed">Completed</option><option value="all">All tasks</option>
      </select>
    </label>
    <p className="mb-3 text-xs text-ink/60">Mark tasks complete yourself when the work is done. You can reopen them later.</p>
    {shown.length ? <ul className="flex flex-col gap-3">{shown.map(item => <MemoryItemEditor key={item.id} memoryId={memoryId} item={item} />)}</ul> : <p className="text-sm text-ink/60">{filter === "open" ? "No open tasks." : filter === "completed" ? "No completed tasks yet." : "No tasks identified."}</p>}
  </>;
}
