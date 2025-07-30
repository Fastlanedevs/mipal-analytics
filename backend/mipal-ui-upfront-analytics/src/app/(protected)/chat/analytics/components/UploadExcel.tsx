import ExcelIcon from "@/assets/svg/ExcelIcon";
import { Button } from "@/components/ui/button";
import React, { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";
import {
  useGetDatabasesQuery,
  useUploadExcelMutation,
} from "@/store/services/analyticsApi";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { useTranslations } from "next-intl";
interface UploadExcelProps {
  isDark: boolean;
  selectedDatabase: any;
}

export default function UploadExcel({
  isDark,
  selectedDatabase,
}: UploadExcelProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [databaseName, setDatabaseName] = useState("");
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const t = useTranslations(
    "chatPage.analyticsPal.dataSourceSelector.uploadExcelFile"
  );
  const [uploadExcel, { isLoading, error }] = useUploadExcelMutation();
  const { refetch } = useGetDatabasesQuery();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setExcelFile(e.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      const formData = new FormData();
      if (excelFile) {
        formData.append("database_name", databaseName);
        formData.append("description", description ?? t("excelDataAnalysis"));
        formData.append("excel_file", excelFile);

        const res = await uploadExcel(formData);
        console.log("excel res", res);

        if (res.data) {
          setDatabaseName("");
          setDescription("");
          setExcelFile(null);

          toast({
            title: t("excelFileUploadedSuccessfully"),
          });

          refetch();
          setIsDialogOpen(false);
        }
        if (res.error) {
          toast({
            title: t("errorUploadingExcelFile"),
            description: t("thereIsAnErrorWithTheFileYouUploaded"),
          });
        }
      }
    } catch (error) {
      console.error(error);
      toast({
        title: t("errorUploadingExcelFile"),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button
        variant="ghost"
        className="w-full justify-start h-auto p-4 group hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl"
        onClick={() => {
          setIsDialogOpen(true);
        }}
      >
        <div className="flex items-start gap-3 w-full">
          <div className="mt-0.5 flex-shrink-0 p-2 rounded-lg bg-primary/10">
            <ExcelIcon
              className="w-5 h-5 text-primary"
              fill={isDark ? "#ffffff" : "#000000"}
            />
          </div>
          <div className="text-left min-w-0 flex-1">
            <div className="font-medium text-sm mb-1 line-clamp-1 flex items-center justify-between text-foreground">
              {t("createANewExcelDatabase")}
              <ChevronRight className="w-4 h-4" />
            </div>
            <div className="text-xs text-muted-foreground opacity-70 text-wrap">
              {t("uploadTheExcelFilesAndAnalyzeDataFromThem")}
            </div>
          </div>
        </div>
      </Button>
      <Toaster />
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">
              {t("uploadExcelFile")}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            <Input
              value={databaseName}
              onChange={(e) => setDatabaseName(e.target.value)}
              placeholder={t("databaseName")}
              className="h-9 placeholder:text-muted-foreground"
            />

            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("description")}
              className="h-9 placeholder:text-muted-foreground"
              rows={3}
            />

            <div className="grid w-full items-center gap-4">
              <Input
                type="file"
                accept=".xlsx,.xls,.xlsm,.xlsb"
                onChange={handleFileChange}
                className="cursor-pointer file:bg-transparent"
              />

              {excelFile && (
                <>
                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center gap-1 bg-muted px-3 py-1 rounded-md text-xs">
                      <span className="max-w-[150px] truncate">
                        {excelFile.name}
                      </span>
                      <button
                        onClick={() => setExcelFile(null)}
                        className="ml-1 hover:bg-muted-foreground/20 rounded-full p-1"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {isSubmitting ? (
              <div className="flex items-center justify-center">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
                <span className="ml-2 text-sm text-muted-foreground">
                  <LoadingTextSimulator />
                </span>
              </div>
            ) : (
              <Button
                variant="default"
                className="h-9 px-4 text-sm font-medium"
                onClick={handleSubmit}
                disabled={!databaseName || excelFile === null}
              >
                {t("submit")}
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

const LoadingTextSimulator = () => {
  const t = useTranslations(
    "chatPage.analyticsPal.dataSourceSelector.uploadExcelFile"
  );
  const loadingTexts = [t("mappingSchema"), t("analyzingData")];

  const [currentText, setCurrentText] = useState(t("uploading"));

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setCurrentText(loadingTexts[index]);
      index++;
      if (index >= loadingTexts.length) {
        index = loadingTexts.length - 1;
      }
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return <>{currentText}</>;
};
