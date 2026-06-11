/**
 * Cells data hooks (TanStack Query). Read-only in Wave-0: the list fans out
 * over every workspace (api/cells.ts), the detail fetches a single cell.
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { cellsApi, type Cell } from "@/api/cells";

/** All cells across every workspace the user can see. */
export function useCellsList(): UseQueryResult<Cell[]> {
  return useQuery({
    queryKey: ["cells"],
    queryFn: () => cellsApi.listAllCells(),
  });
}

/** A single cell by id. Disabled until an id is available. */
export function useCell(cellId: string | undefined): UseQueryResult<Cell> {
  return useQuery({
    queryKey: ["cells", cellId],
    queryFn: () => cellsApi.getCell(cellId as string),
    enabled: !!cellId,
  });
}
