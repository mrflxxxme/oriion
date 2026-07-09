/**
 * Recent-tasks store (Dashboard summary surface).
 *
 * There is no backend list-tasks endpoint yet (CellDetailPage's "recent
 * tasks" tab has carried a "Wave-0: no list endpoint yet" placeholder
 * comment since Wave 0), so the Dashboard's "recent tasks" section tracks
 * the ids of tasks the app itself created (today: only the onboarding
 * wizard's first-task step) and re-fetches each one's live status via the
 * existing per-task GET (tasks/hooks.ts's `useTask` — see
 * `dashboard/hooks.ts`'s `useRecentTaskSummaries`).
 *
 * Persisted to localStorage so a page reload still shows the same summary;
 * capped at RECENT_TASKS_LIMIT, newest first, de-duplicated by task id.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface RecentTaskRef {
  cellId: string;
  taskId: string;
  title: string;
  createdAt: string;
}

const RECENT_TASKS_LIMIT = 10;

interface RecentTasksState {
  recentTasks: RecentTaskRef[];
  addRecentTask: (ref: RecentTaskRef) => void;
}

export const useRecentTasksStore = create<RecentTasksState>()(
  persist(
    (set) => ({
      recentTasks: [],
      addRecentTask: (ref) => {
        set((state) => ({
          recentTasks: [ref, ...state.recentTasks.filter((t) => t.taskId !== ref.taskId)].slice(
            0,
            RECENT_TASKS_LIMIT,
          ),
        }));
      },
    }),
    { name: "oriion-recent-tasks" },
  ),
);
