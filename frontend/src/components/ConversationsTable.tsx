"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { deleteConversation, listConversations } from "@/lib/api";
import { formatDate, formatFileSize } from "@/lib/format";
import { StatusBadge } from "./StatusBadge";
import { WaveformMark } from "./WaveformMark";

export function ConversationsTable() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
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

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-16 text-center">
        <WaveformMark className="h-6 w-auto text-ink/20" />
        <p className="text-sm font-medium text-ink">No conversations yet</p>
        <p className="text-xs text-ink/50">Upload a recording above to get started.</p>
      </div>
    );
  }

  return (
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
        {data.map((conversation) => (
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
  );
}
