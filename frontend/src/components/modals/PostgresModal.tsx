import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useCreateIntegrationMutation } from "@/store/services/integrationApi";
import { Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";

interface PostgresModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PostgresFormData {
  database_name: string;
  host: string;
  port: number;
  username: string;
  password: string;
  description: string;
}

export function PostgresModal({ isOpen, onClose }: PostgresModalProps) {
  const { toast } = useToast();
  const t = useTranslations("integration.postgresModal");
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [createIntegration] = useCreateIntegrationMutation();
  const [formData, setFormData] = useState<PostgresFormData>({
    database_name: "",
    host: "",
    port: 5432,
    username: "",
    password: "",
    description: "",
  });

  // Reset form when modal closes
  const handleClose = () => {
    setFormData({
      database_name: "",
      host: "",
      port: 5432,
      username: "",
      password: "",
      description: "",
    });
    setShowPassword(false);
    onClose();
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "port" ? parseInt(value) || "" : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await createIntegration({
        integration_type: "POSTGRESQL",
        credential: {
          database_name: formData.database_name,
          host: formData.host,
          port: formData.port,
          username: formData.username,
          password: formData.password,
          description: formData.description,
        },
        expires_at: new Date(
          Date.now() + 365 * 24 * 60 * 60 * 1000
        ).toISOString(), // 1 year from now
        settings: {},
      });

      if ("error" in response) {
        const errorData = response.error as any;
        const errorMessage =
          errorData?.data?.error ||
          errorData?.data?.message ||
          t("failedToConnectToPostgreSQLDatabase");
        throw new Error(errorMessage);
      }

      toast({
        title: t("success"),
        description: t("successfullyConnectedToPostgreSQLDatabase"),
      });
      onClose();
    } catch (error) {
      console.error("Connection error:", error);
      toast({
        title: t("error"),
        description:
          error instanceof Error ? error.message : t("connectionFailed"),
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t("connectPostgreSQLDatabase")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="database_name" className="text-right">
                {t("database")}
              </Label>
              <Input
                id="database_name"
                name="database_name"
                value={formData.database_name}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="postgres"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="host" className="text-right">
                {t("host")}
              </Label>
              <Input
                id="host"
                name="host"
                value={formData.host}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="db-postgres.example.com"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="port" className="text-right">
                {t("port")}
              </Label>
              <Input
                id="port"
                name="port"
                type="number"
                value={formData.port}
                onChange={handleInputChange}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="username" className="text-right">
                {t("username")}
              </Label>
              <Input
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="postgres"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="password" className="text-right">
                {t("password")}
              </Label>
              <div className="col-span-3 relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={handleInputChange}
                  className="pr-10"
                  placeholder="********"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                  <span className="sr-only">
                    {showPassword ? t("hidePassword") : t("showPassword")}
                  </span>
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">
                {t("description")}
              </Label>
              <Textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder={t("enterADescriptionForThisConnection")}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? t("connecting") : t("connect")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
