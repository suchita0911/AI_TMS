import { toast } from "sonner";

/**
 * Standard success toast shown after deleting an entry — used app-wide so every
 * delete reads and looks the same. Pass the entity label (e.g. "Course") and,
 * when available, the specific item's name for a clearer confirmation.
 */
export function notifyDeleted(entity: string, name?: string) {
  toast.success(`${entity} deleted`, {
    description: name
      ? `“${name}” was deleted successfully.`
      : `The ${entity.toLowerCase()} was deleted successfully.`,
  });
}
