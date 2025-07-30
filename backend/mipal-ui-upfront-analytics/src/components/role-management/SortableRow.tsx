import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { GripVertical, Pencil, Trash2 } from "lucide-react";

interface Role {
  id: string;
  name: string;
  priority: number;
  permissions: string[];
  users: number;
}

interface SortableRowProps {
  role: Role;
}

export function SortableRow({ role }: SortableRowProps) {
  const {
    attributes,
    listeners,
    transform,
    transition,
    setNodeRef,
    isDragging,
  } = useSortable({ id: role.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <TableRow
      ref={setNodeRef}
      style={style}
      className={`${isDragging ? "opacity-50" : ""} relative`}
    >
      <TableCell>
        <Button
          variant="ghost"
          size="sm"
          className="cursor-grab"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="w-4 h-4" />
        </Button>
      </TableCell>
      <TableCell className="font-medium">{role.name}</TableCell>
      <TableCell>{role.priority}</TableCell>
      <TableCell>{role.permissions.join(", ")}</TableCell>
      <TableCell>{role.users}</TableCell>
      <TableCell className="text-right space-x-2">
        <Button variant="ghost" size="sm">
          <Pencil className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-red-500 hover:text-red-700"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
}
