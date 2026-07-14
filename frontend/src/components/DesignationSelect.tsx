import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Check, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, apiError } from "@/lib/api";
import { DESIGNATIONS } from "@/types";

const ADD_NEW = "__add_new__";

interface Designation {
  id: number;
  name: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  /** Show the inline "add new designation" option (admins only). */
  allowAdd?: boolean;
  /** Which endpoint to read the catalogue from. */
  source?: "admin" | "public";
  placeholder?: string;
  triggerClassName?: string;
}

export function DesignationSelect({
  value,
  onChange,
  allowAdd = false,
  source = "admin",
  placeholder = "Select designation",
  triggerClassName,
}: Props) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");

  const endpoint = source === "public" ? "/auth/designations" : "/designations";
  const { data } = useQuery({
    queryKey: ["designations", source],
    queryFn: async () => (await api.get<Designation[]>(endpoint)).data,
  });

  // Prefer the live catalogue; fall back to the bundled list if it's empty
  // (e.g. offline). Always include the current value so it stays selectable.
  const fetched = (data ?? []).map((d) => d.name);
  const base = fetched.length ? fetched : [...DESIGNATIONS];
  const names = Array.from(new Set([...(value ? [value] : []), ...base]));

  const createDesignation = useMutation({
    mutationFn: async (name: string) =>
      (await api.post<Designation>("/designations", { name })).data,
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["designations"] });
      onChange(d.name);
      setAdding(false);
      setNewName("");
      toast.success(`Added designation “${d.name}”`);
    },
    onError: (e) => toast.error(apiError(e, "Could not add designation")),
  });

  const submitNew = () => {
    const name = newName.trim();
    if (name.length < 2) {
      toast.error("Enter a designation name (min 2 characters).");
      return;
    }
    createDesignation.mutate(name);
  };

  if (adding) {
    return (
      <div className="flex items-center gap-2">
        <Input
          autoFocus
          value={newName}
          placeholder="New designation, e.g. Solutions Architect"
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submitNew();
            } else if (e.key === "Escape") {
              setAdding(false);
              setNewName("");
            }
          }}
        />
        <Button
          type="button"
          size="icon"
          onClick={submitNew}
          disabled={createDesignation.isPending}
          title="Add"
        >
          {createDesignation.isPending ? <Spinner /> : <Check className="h-4 w-4" />}
        </Button>
        <Button
          type="button"
          size="icon"
          variant="outline"
          onClick={() => {
            setAdding(false);
            setNewName("");
          }}
          title="Cancel"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <Select
      value={value}
      onValueChange={(v) => {
        if (v === ADD_NEW) {
          setAdding(true);
          return;
        }
        onChange(v);
      }}
    >
      <div className={triggerClassName ? `${triggerClassName} relative` : "relative"}>
        <SelectTrigger className={value ? "pr-10" : undefined}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        {value && (
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            onPointerDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
            }}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onChange("");
            }}
            title="Clear selected designation"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      <SelectContent>
        {allowAdd && (
          <SelectItem value={ADD_NEW} className="text-primary">
            <span className="flex items-center gap-1.5">
              <Plus className="h-4 w-4" /> Add new designation…
            </span>
          </SelectItem>
        )}
        {names.map((n) => (
          <SelectItem key={n} value={n}>
            {n}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
