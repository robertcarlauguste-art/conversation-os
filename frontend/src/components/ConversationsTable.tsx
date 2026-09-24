"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { deleteConversation, listConversations } from "@/lib/api";
import { conversationTitle, formatDate, formatFileSize } from "@/lib/format";
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
    placeholderData: previous => previous,
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
        Couldn&apos;t load conversations. Please refresh the page and try again.
      </p>
    );
  }

  if (!data || (data.length === 0 && page === 0 && !deferredSearch && !status)) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-16 text-center">
        <WaveformMark className="h-6 w-auto text-ink/20" />
        <p className="text-sm font-medium text-ink">No conversations yet</p>
        <p className="text-xs text-ink/50">Record a voice note or upload audio above to get started.</p>
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
          <option value="UPLOADED">Received</option>
          <option value="QUEUED">Waiting to start</option>
          <option value="PROCESSING">Preparing your notes</option>
          <option value="COMPLETED">Ready to review</option>
          <option value="FAILED">Needs attention</option>
        </select>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line py-10 text-center text-sm text-ink/50">
          No conversations match these filters.
        </p>
      ) : (
      <table className="block w-full min-w-0 text-sm md:table md:border-collapse md:rounded-xl md:border md:border-line md:bg-surface">
      <thead className="hidden md:table-header-group">
        <tr className="border-b border-line bg-paper text-left text-xs uppercase tracking-wide text-ink/50">
          <th className="px-4 py-3 font-medium">Title</th>
          <th className="px-4 py-3 font-medium">Status</th>
          <th className="px-4 py-3 font-medium">Uploaded</th>
          <th className="px-4 py-3 font-medium">File Size</th>
          <th className="px-4 py-3 font-medium">Actions</th>
        </tr>
      </thead>
      <tbody className="block space-y-3 md:table-row-group md:space-y-0">
        {rows.map((conversation) => (
          <tr key={conversation.id} className="block min-w-0 rounded-xl border border-line bg-surface p-3 md:table-row md:rounded-none md:border-x-0 md:border-t-0 md:p-0">
            <td className="block min-w-0 px-1 py-2 md:table-cell md:px-4 md:py-3">
              <Link
                href={`/conversations/${conversation.id}`}
                className="break-all font-medium text-ink hover:text-accent"
              >
                {conversationTitle(conversation)}
              </Link>
            </td>
            <td className="block min-w-0 px-1 py-2 md:table-cell md:px-4 md:py-3">
              <StatusBadge status={conversation.status} />
              {conversation.is_stale && <span className="ml-2 text-amber-700">Taking longer than expected</span>}
            </td>
            <td className="block px-1 py-1 text-ink/70 md:table-cell md:px-4 md:py-3"><span className="md:hidden">Uploaded: </span>{formatDate(conversation.created_at)}</td>
            <td className="block px-1 py-1 text-ink/70 md:table-cell md:px-4 md:py-3"><span className="md:hidden">File size: </span>{formatFileSize(conversation.file_size)}</td>
            <td className="block min-w-0 px-1 py-2 md:table-cell md:px-4 md:py-3">
              <div className="flex gap-3">
                <Link
                  href={`/conversations/${conversation.id}`}
                  className="inline-flex min-h-11 items-center text-sm font-medium text-steel hover:underline"
                >
                  View
                </Link>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(conversation.id)}
                  className="min-h-11 text-sm font-medium text-status-failed hover:underline disabled:opacity-50"
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
