"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Cross2Icon } from "@radix-ui/react-icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (role: { name: string; permissions: string[] }) => void;
}

export function RoleModal({ open, onOpenChange, onSubmit }: ModalProps) {
  const [roleName, setRoleName] = useState("");
  const [permissions, setPermissions] = useState("");

  const handleSubmit = () => {
    onSubmit({ name: roleName, permissions: permissions.split(",") });
    setRoleName("");
    setPermissions("");
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Trigger asChild>
        <Button>Add Role</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 bg-white p-6 rounded-lg shadow-lg">
          <Dialog.Title className="text-lg font-medium">
            Add New Role
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-gray-500">
            Enter the details for the new role.
          </Dialog.Description>
          <div className="mt-4 space-y-4">
            <Input
              placeholder="Role Name"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
            />
            <Input
              placeholder="Permissions (comma separated)"
              value={permissions}
              onChange={(e) => setPermissions(e.target.value)}
            />
          </div>
          <div className="mt-6 flex justify-end space-x-2">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>Add Role</Button>
          </div>
          <Dialog.Close asChild>
            <button
              className="absolute top-3 right-3 text-gray-500 hover:text-gray-700"
              aria-label="Close"
            >
              <Cross2Icon />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
