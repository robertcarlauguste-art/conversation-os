"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { deleteConversation, listConversations } from "@/lib/api";
import { formatDate, formatFileSize } from "@/lib/format";
import { StatusBadge } from "./StatusBadge";
import { WaveformMark } from "./WaveformMark";

export function ConversationsTable() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const pageSize = 20;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations", page, deferredSearch, status],
    queryFn: () =>
      listConversations({
        limit: pageSize + 1,
        offset: page * pageSize,
        search: deferredSearch || undefined,
        status: status || undefined,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });

  if (isLoading) {
    return <p className="py-10 text-center text-sm text-ink/50">Loading conversations…</p>;
  }

  if (isError) {
    return (
      <p className="py-10 text-center text-sm text-status-failed">
        Couldn&apos;t load conversations. Check that the backend is running.
      </p>
    );
  }

  if (!data || (data.length === 0 && page === 0)) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-16 text-center">
        <WaveformMark className="h-6 w-auto text-ink/20" />
        <p className="text-sm font-medium text-ink">No conversations yet</p>
        <p className="text-xs text-ink/50">Upload a recording above to get started.</p>
      </div>
    );
  }

  const rows = data.slice(0, pageSize);
  const hasNextPage = data.length > pageSize;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          placeholder="Search title or filename"
          aria-label="Search conversations"
          className="min-w-0 flex-1 rounded-md border border-line bg-surface px-3 py-2 text-sm"
        />
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(0);
          }}
          aria-label="Filter conversation status"
          className="rounded-md border border-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="UPLOADED">Uploaded</option>
          <option value="QUEUED">Queued</option>
          <option value="PROCESSING">Processing</option>
          <option value="COMPLETED">Completed</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line py-10 text-center text-sm text-ink/50">
          No conversations match these filters.
        </p>
      ) : (
      <table className="w-full border-collapse overflow-hidden rounded-xl border border-line bg-surface text-sm">
      <thead>
        <tr className="border-b border-line bg-paper text-left text-xs uppercase tracking-wide text-ink/50">
          <th className="px-4 py-3 font-medium">Title</th>
          <th className="px-4 py-3 font-medium">Status</th>
          <th className="px-4 py-3 font-medium">Uploaded</th>
          <th className="px-4 py-3 font-medium">File Size</th>
          <th className="px-4 py-3 font-medium">Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((conversation) => (
          <tr key={conversation.id} className="border-b border-line last:border-0">
            <td className="px-4 py-3">
              <Link
                href={`/conversations/${conversation.id}`}
                className="font-medium text-ink hover:text-accent"
              >
                {conversation.title ?? "Untitled conversation"}
              </Link>
            </td>
            <td className="px-4 py-3">
              <StatusBadge status={conversation.status} />
              {conversation.is_stale && <span className="ml-2 text-amber-700">Possibly stalled</span>}
            </td>
            <td className="px-4 py-3 text-ink/70">{formatDate(conversation.created_at)}</td>
            <td className="px-4 py-3 text-ink/70">{formatFileSize(conversation.file_size)}</td>
            <td className="px-4 py-3">
              <div className="flex gap-3">
                <Link
                  href={`/conversations/${conversation.id}`}
                  className="text-xs font-medium text-steel hover:underline"
                >
                  View
                </Link>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(conversation.id)}
                  className="text-xs font-medium text-status-failed hover:underline disabled:opacity-50"
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
      </table>
      )}
      <div className="flex items-center justify-between text-sm text-ink/60">
        <span>Page {page + 1}</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            disabled={page === 0}
            className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((value) => value + 1)}
            disabled={!hasNextPage}
            className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
