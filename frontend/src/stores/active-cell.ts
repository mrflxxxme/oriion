/**
 * Active-cell store — tracks the cell the user is currently viewing/working in.
 *
 * Wave-0 scope: in-memory only (no persistence). The CellDetailPage sets it on
 * mount so downstream features (task submit) can read the current cell without
 * prop-drilling through the router.
 */
import { create } from "zustand";

interface ActiveCellState {
  activeCellId: string | null;
  setActiveCell: (id: string | null) => void;
}

export const useActiveCellStore = create<ActiveCellState>()((set) => ({
  activeCellId: null,
  setActiveCell: (id) => {
    set({ activeCellId: id });
  },
}));
