import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import { ClientMergeHistory } from "./ClientMergeHistory";

const api = vi.hoisted(() => ({listClientMerges: vi.fn(), undoClientMerge: vi.fn()}));
vi.mock("@/lib/api", () => api);
beforeEach(() => { vi.clearAllMocks(); api.listClientMerges.mockResolvedValue([{id:'merge1',source_name:'Mari',target_name:'Marie',created_at:'2026-10-04T12:00:00Z',undone_at:null,supports_undo:true}]); });
function show() { render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ClientMergeHistory /></QueryClientProvider>); fireEvent.click(screen.getByText('Recent merges & undo')); }

it('requires confirmation, allows cancel, and reports successful restoration', async () => {
  show(); fireEvent.click(await screen.findByText('Undo merge'));
  expect(api.undoClientMerge).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Cancel'));
  expect(screen.queryByText('Confirm undo merge')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Undo merge'));
  api.undoClientMerge.mockResolvedValue({source_id:'a',target_id:'b'});
  fireEvent.click(screen.getByText('Confirm undo merge'));
  await waitFor(() => expect(api.undoClientMerge).toHaveBeenCalledWith('merge1'));
  expect(await screen.findByRole('status')).toHaveTextContent('Merge undone');
});

it('shows conflict without claiming success', async () => {
  api.undoClientMerge.mockRejectedValue(new Error('Records changed. Undo stopped to protect newer work.'));
  show(); fireEvent.click(await screen.findByText('Undo merge')); fireEvent.click(screen.getByText('Confirm undo merge'));
  expect(await screen.findByRole('alert')).toHaveTextContent('protect newer work');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('does not offer automatic undo for older merges', async () => {
  api.listClientMerges.mockResolvedValue([{id:'old',source_name:'Mari',target_name:'Marie',created_at:'2026-10-04T12:00:00Z',supports_undo:false}]);
  show(); expect(await screen.findByText('This older merge needs manual recovery review.')).toBeInTheDocument();
  expect(screen.queryByText('Undo merge')).not.toBeInTheDocument();
});
