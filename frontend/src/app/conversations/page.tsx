import { ConversationsTable } from "@/components/ConversationsTable";
import { UploadDropzone } from "@/components/UploadDropzone";

export default function ConversationsPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Conversations</h1>
        <p className="mt-1 text-sm text-ink/60">
          Every recording that has entered ConversationOS, newest first.
        </p>
      </div>
      <UploadDropzone />
      <ConversationsTable />
    </div>
  );
}
