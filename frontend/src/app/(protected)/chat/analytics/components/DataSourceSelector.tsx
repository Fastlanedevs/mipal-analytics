"use client";

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { Button } from "@/components/ui/button";
import {
  Database,
  FileUp,
  X,
  Blocks,
  FileSpreadsheet,
  Table,
  ChevronRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { ActionButton } from "./shared/Buttons";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { toast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Database as DataSource,
  TableStats,
  useGetDatabasesQuery,
  useUploadCSVMutation,
  useUploadFilesToDatabaseMutation,
} from "@/store/services/analyticsApi";
import {
  setSelectedDatabase,
  setSelectedTable,
  setTables,
} from "@/store/slices/analyticsSlice";
import { ArtifactTabs } from "./ArtifactRenderer/ArtifactTabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import { Message } from "../../types/chat";
import CSVIcon from "@/assets/svg/CSVIcon";
import PostgresSQLIcon from "@/assets/svg/PostgresSQLIcon";
import { useTheme } from "@/contexts/ThemeContext";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ExcelIcon from "@/assets/svg/ExcelIcon";
import { cn } from "@/lib/utils";
import UploadExcel from "./UploadExcel";
import { useTranslations } from "next-intl";

export const DataSourceSelector = () => {
  const t = useTranslations("chatPage.analyticsPal.dataSourceSelector");
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [databaseName, setDatabaseName] = useState("");
  const [csvFiles, setCsvFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const messages = useSelector((state: RootState) => state.chat.messages);

  const { theme } = useTheme();
  const isDark = useMemo(
    () =>
      theme === "dark" ||
      (theme === "system" &&
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches),
    [theme]
  );

  const dispatch = useDispatch();

  // Get all databases
  const {
    data: databases,
    isLoading: databasesLoading,
    isFetching: databasesFetching,
    refetch,
  } = useGetDatabasesQuery();

  // Get the selected database and table
  const { selectedDatabase, selectedTable } = useSelector(
    (state: RootState) => state.analytics
  );

  const [uploadCSV, { isLoading: isUploading }] = useUploadCSVMutation();
  const [uploadFilesToDatabase, { isLoading: isUploadingFiles }] =
    useUploadFilesToDatabaseMutation();

  const handleDataSourceSelect = (
    source: DataSource,
    type: string,
    name: string,
    table?: TableStats[]
  ) => {
    dispatch(setSelectedDatabase(source));
  };

  useEffect(() => {
    if (!databases) {
      return;
    }

    const firstMessageArray = Object.values(messages)[0];
    const allMessages =
      Array.isArray(firstMessageArray) && firstMessageArray.length > 0
        ? firstMessageArray
        : undefined;
    // check all messages for database_uid
    const selectedDb = allMessages?.find(
      (message: Message) => message.database_uid
    );
    const selectedTble = allMessages?.find(
      (message: Message) => message.table_uid
    );
    if (selectedDb) {
      const database = databases?.find(
        (database) => database.uid === selectedDb.database_uid
      );
      if (database) {
        dispatch(setSelectedDatabase(database));
      }
    }
    if (selectedTble) {
      const tableDB = databases?.find((database) =>
        database.tables.find((table) => table.uid === selectedTble.table_uid)
      );
      const table = tableDB?.tables.find(
        (table) => table.uid === selectedTble.table_uid
      );
      if (table) {
        dispatch(setSelectedTable(table as unknown as TableStats));
      }
    }
  }, [databases, messages]);

  const artifacts = useSelector(
    (state: RootState) => state.artifacts.artifacts
  );

  const handleTableSelect = (table: TableStats) => {
    dispatch(setSelectedTable(table));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      // Convert FileList to Array and filter for .csv files
      const files = Array.from(e.target.files).filter((file) =>
        file.name.endsWith(".csv")
      );
      setCsvFiles(files);
    }
  };

  const handleUploadClick = () => {
    if (selectedDatabase) {
      setDatabaseName(selectedDatabase.name);
    }
    setIsDialogOpen(true);
  };

  const removeFile = (indexToRemove: number) => {
    setCsvFiles((files) => files.filter((_, index) => index !== indexToRemove));
  };

  const handleSubmitDB = async () => {
    if (csvFiles.length === 0) {
      toast({
        title: t("pleaseSelectAtLeastOneCSVFile"),
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();

      // Add each CSV file to the form data with the name "files"
      csvFiles.forEach((attachment) => {
        formData.append("files", attachment);
      });

      // Add database name to the form data
      formData.append("database_name", databaseName);

      // Make the API call to upload CSV files
      const response = await uploadCSV(formData);

      if (!response.data) {
        console.error("Error response:", response.error);
        toast({
          title: t("failedToSetupDatabase"),
          variant: "destructive",
        });
        return;
      }

      refetch();

      setCsvFiles([]);

      toast({
        title: t("databaseSetupSuccessfully"),
        description: `(${t("addedDatabase")}): ${databaseName}`,
      });

      setIsDialogOpen(false);
    } catch (error) {
      console.error("Error uploading CSV files:", error);
      toast({
        title: t("failedToSetupDatabase"),
        description: error instanceof Error ? error.message : t("unknownError"),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (!isDialogOpen) {
      setCsvFiles([]);
    }
  }, [isDialogOpen]);

  const handleSubmitCSV = async () => {
    try {
      setIsSubmitting(true);

      if (csvFiles.length === 0) {
        toast({
          title: t("noFilesSelected"),
          description: t("pleaseSelectAtLeastOneCSVFileToUpload"),
          variant: "destructive",
        });
        return;
      }

      const formData = new FormData();

      // Add all CSV files to the FormData
      csvFiles.forEach((attachment) => {
        formData.append("files", attachment);
      });

      const response = await uploadFilesToDatabase({
        databaseUid: selectedDatabase?.uid || "",
        formData,
      });

      if (!response.data) {
        console.error("Error response:", response.error);
        toast({
          title: t("failedToGenerateTables"),
          variant: "destructive",
        });
        return;
      }

      toast({
        title: t("csvFilesUploadedSuccessfully"),
        description: `(${t("uploadedFiles")}): ${csvFiles.length}`,
      });

      // Update the store with the new database
      if (response?.data?.tables) {
        dispatch(setTables(response.data.tables || []));
        dispatch(
          setSelectedTable(
            response.data.tables?.[response.data.tables.length - 1] || null
          )
        );
      }

      setIsDialogOpen(false);
    } catch (error) {
      console.error("Error uploading CSV files:", error);
      toast({
        title: t("failedToUploadCSVFiles"),
        description: error instanceof Error ? error.message : "",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleHideDbCloseButton = useCallback(() => {
    const firstMessageArray = Object.values(messages)[0];
    const allMessages =
      Array.isArray(firstMessageArray) && firstMessageArray.length > 0
        ? firstMessageArray
        : undefined;
    // check all messages for database_uid
    const selectedDb = allMessages?.find(
      (message: Message) => message.database_uid
    );

    if (selectedDb) {
      const database = databases?.find(
        (database) => database.uid === selectedDb.database_uid
      );
      if (database) {
        return true;
      }
    }
    return false;
  }, [messages, databases]);

  const handleHideTableCloseButton = useCallback(() => {
    const firstMessageArray = Object.values(messages)[0];
    const allMessages =
      Array.isArray(firstMessageArray) && firstMessageArray.length > 0
        ? firstMessageArray
        : undefined;
    // check all messages for table_uid
    const selectedTble = allMessages?.find(
      (message: Message) => message.table_uid
    );
    if (selectedTble) {
      const table = databases?.find((database) =>
        database.tables.find((table) => table.uid === selectedTble.table_uid)
      );
      if (table) {
        return true;
      }
    }
    return false;
  }, [messages, databases]);

  const handleIconComponent = (type: string) => {
    switch (type) {
      case "postgres":
        return PostgresSQLIcon;
      case "csv":
        return CSVIcon;
      case "excel":
        return ExcelIcon;
      default:
        return CSVIcon;
    }
  };

  return (
    <div className="flex flex-col gap-2 flex-1">
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept=".csv,text/csv"
        multiple
        onChange={handleFileChange}
      />
      <div className="space-y-2 sticky top-0 bg-background/80 dark:bg-muted/10 backdrop-blur-sm z-[100] py-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-lg font-semibold">
            {!selectedDatabase ? t("selectADatabase") : t("database")}
          </h3>
          <div className="h-[1px] flex-1 bg-foreground/30 dark:bg-foreground/90"></div>

          <div className="flex items-center gap-2">
            {selectedDatabase && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border bg-foreground/90 dark:bg-foreground text-background max-w-[200px]">
                {selectedDatabase.type === "postgres" ? (
                  <PostgresSQLIcon
                    className="w-4 h-4 flex-shrink-0"
                    fill={isDark ? "#000000" : "#ffffff"}
                  />
                ) : selectedDatabase.type === "excel" ? (
                  <ExcelIcon
                    className="w-4 h-4 flex-shrink-0"
                    fill={isDark ? "#000000" : "#ffffff"}
                  />
                ) : selectedDatabase.type === "excel" ? (
                  <ExcelIcon
                    className="w-4 h-4 flex-shrink-0"
                    fill={isDark ? "#000000" : "#ffffff"}
                  />
                ) : (
                  <CSVIcon
                    className="w-4 h-4 flex-shrink-0"
                    fill={isDark ? "#000000" : "#ffffff"}
                  />
                )}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-sm text-background truncate">
                        {selectedDatabase.name}
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{selectedDatabase.name}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                {handleHideDbCloseButton() ? null : (
                  <button
                    className="ml-2 hover:bg-accent hover:text-foreground rounded-full p-1"
                    onClick={() => {
                      dispatch(setSelectedDatabase(null));
                      dispatch(setSelectedTable(null));
                      dispatch(removeArtifacts());
                    }}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}

            {selectedTable && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border bg-foreground/90 dark:bg-foreground text-background  max-w-[200px]">
                <Table className="w-4 h-4 flex-shrink-0" />
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-sm text-background truncate">
                        {selectedTable.name}
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{selectedTable.name}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {handleHideTableCloseButton() ? null : (
                  <button
                    className="ml-2 hover:bg-accent hover:text-foreground rounded-full p-1"
                    onClick={() => {
                      dispatch(setSelectedTable(null));
                      dispatch(removeArtifacts());
                    }}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
        {!selectedDatabase ? (
          <p className="text-sm text-muted-foreground">
            {t("chooseADataSourceToAnalyzeYourData")}
          </p>
        ) : (
          !(selectedDatabase?.type === "postgres" || selectedTable) && (
            <p className="text-sm text-muted-foreground">
              {t("chooseATableToAnalyzeYourData")}
            </p>
          )
        )}
      </div>
      <AnimatePresence mode="wait">
        {selectedDatabase ? (
          <motion.div
            key="selected"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className={"w-full space-y-2"}
          >
            {selectedDatabase && (
              <div className="">
                {/* If the database is a CSV database, show the table selector */}
                {(selectedDatabase.type === "csv" ||
                  selectedDatabase.type === "excel") &&
                !selectedTable &&
                selectedDatabase?.tables.length > 0 ? (
                  <div className="flex items-center gap-2">
                    <Select
                      onValueChange={(value) => {
                        const table = selectedDatabase.tables.find(
                          (t: TableStats) => t.name === value
                        );
                        if (table) handleTableSelect(table);
                      }}
                    >
                      <SelectTrigger className="w-[250px] h-9">
                        <SelectValue
                          placeholder={
                            selectedDatabase.type === "excel"
                              ? t("selectASheet")
                              : t("selectATable")
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {selectedDatabase.tables &&
                        selectedDatabase.tables.length > 0 ? (
                          selectedDatabase.tables.map(
                            (table: TableStats, index: number) => (
                              <SelectItem
                                key={table.uid || index}
                                value={table.name}
                              >
                                <div className="flex items-center gap-2">
                                  <Table className="w-4 h-4" />
                                  {/* <CSVIcon className="w-4 h-4" /> */}
                                  {table.name}
                                </div>
                              </SelectItem>
                            )
                          )
                        ) : (
                          <SelectItem value="" disabled>
                            <span className="text-sm text-muted-foreground">
                              {t("noTablesAvailableInThisCSV")}
                            </span>
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    {/* Add a button to add new CSV files */}
                    <Button
                      variant="outline"
                      className={cn(
                        "w-fit flex items-center gap-2 px-3 py-2 shadow-none",
                        selectedDatabase.type === "excel" && "hidden"
                      )}
                      onClick={handleUploadClick}
                    >
                      <FileUp className="w-4 h-4" />
                      {t("addNewCSVTables")}
                    </Button>
                  </div>
                ) : (
                  // If the database is a CSV/Excel database and there are no tables, show a message
                  selectedDatabase &&
                  selectedDatabase.tables.length === 0 && (
                    <p className="text-sm text-muted-foreground border py-1 px-2 rounded-md text-center border-dashed w-fit">
                      {t("noTablesAvailableInThisDatabase")}
                    </p>
                  )
                )}
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="options"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="w-full space-y-2 analytics-add-database"
          >
            {databasesLoading || databasesFetching ? (
              <div className="space-y-2">
                <div className="animate-pulse">
                  <div className="w-full p-4 border border-border rounded-2xl">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex-shrink-0 w-9 h-9 bg-muted rounded-lg"></div>
                      <div className="flex-1">
                        <div className="h-4 w-1/3 bg-muted rounded mb-2"></div>
                        <div className="h-3 w-2/3 bg-muted rounded"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {databases?.map((source: DataSource, index: number) => {
                  // Create the appropriate icon component
                  const IconComponent = handleIconComponent(source.type);

                  // Use provided fill, or determine based on theme
                  const iconFill = isDark ? "#ffffff" : "#000000";

                  return (
                    <Button
                      key={index}
                      variant="ghost"
                      className="w-full justify-start h-auto p-4 group hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl"
                      onClick={() =>
                        handleDataSourceSelect(
                          source,
                          source.type,
                          source.name,
                          source.tables
                        )
                      }
                    >
                      <div className="flex items-start gap-3 w-full">
                        <div className="mt-0.5 flex-shrink-0 p-2 rounded-lg bg-primary/10">
                          <IconComponent
                            className="w-5 h-5 text-primary"
                            fill={iconFill}
                          />
                        </div>
                        <div className="text-left min-w-0 flex-1">
                          <div className="font-medium text-sm mb-1 line-clamp-1 flex items-center justify-between text-foreground">
                            {source.name}
                            <ChevronRight className="w-4 h-4" />
                          </div>
                          <div className="text-xs text-muted-foreground opacity-70 text-wrap">
                            {source.description ||
                              (source.type === "postgres"
                                ? t("postgreSQLDatabase")
                                : t("csvDatabase"))}
                          </div>
                        </div>
                      </div>
                    </Button>
                  );
                })}
              </>
            )}
            {(databasesLoading ||
              databasesFetching ||
              (databases && databases?.length > 0)) && (
              <div className="flex items-center gap-4">
                <div className="h-[1px] flex-1 bg-border"></div>
                <span className="text-xs text-muted-foreground font-medium">
                  {t("or")}
                </span>
                <div className="h-[1px] flex-1 bg-border"></div>
              </div>
            )}

            {/* Add or Create a new Database (Postgres or CSV) */}
            {!(selectedDatabase?.type === "postgres" || selectedTable) && (
              <>
                <ActionButton
                  icon={Blocks}
                  title={t("connectMoreIntegrations")}
                  description={t(
                    "setUpAdditionalDataSourceConnectionsInTheIntegrationsPage"
                  )}
                  onClick={() => router.push(`/integration`)}
                />
                {!(databasesLoading || databasesFetching) &&
                  (!databases || databases?.length === 0) && (
                    <div className="flex items-center gap-4">
                      <div className="h-[1px] flex-1 bg-border"></div>
                      <span className="text-xs text-muted-foreground font-medium">
                        {t("or")}
                      </span>
                      <div className="h-[1px] flex-1 bg-border"></div>
                    </div>
                  )}
                <Button
                  variant="ghost"
                  className="w-full justify-start h-auto p-4 group hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl"
                  onClick={() => {
                    selectedDatabase && dispatch(setSelectedDatabase(null));
                    selectedTable && dispatch(setSelectedTable(null));
                    setDatabaseName("");
                    handleUploadClick();
                  }}
                >
                  <div className="flex items-start gap-3 w-full">
                    <div className="mt-0.5 flex-shrink-0 p-2 rounded-lg bg-primary/10">
                      <CSVIcon
                        className="w-5 h-5 text-primary"
                        fill={isDark ? "#ffffff" : "#000000"}
                      />
                    </div>
                    <div className="text-left min-w-0 flex-1">
                      <div className="font-medium text-sm mb-1 line-clamp-1 flex items-center justify-between text-foreground">
                        {t("createANewCSVDatabase")}
                        <ChevronRight className="w-4 h-4" />
                      </div>
                      <div className="text-xs text-muted-foreground opacity-70 text-wrap">
                        {t("uploadTheCSVFilesAndAnalyzeDataFromThem")}
                      </div>
                    </div>
                  </div>
                </Button>
                <UploadExcel
                  isDark={isDark}
                  selectedDatabase={selectedDatabase}
                />
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-6 sm:gap-10 divide-y divide-border">
        <AnimatePresence mode="wait">
          {(selectedDatabase?.type === "postgres" || selectedTable) &&
            (databasesLoading || databasesFetching ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="flex flex-col gap-2"
              >
                {/* Skeleton loading remains the same */}
                <div className="flex gap-2">
                  {[1, 2, 3].map((tab) => (
                    <div
                      key={tab}
                      className="h-10 w-24 bg-muted animate-pulse rounded-lg flex-1"
                    />
                  ))}
                </div>
                <div className="border rounded-2xl p-6">
                  <div className="space-y-3">
                    <div className="h-4 bg-muted animate-pulse rounded-lg w-3/4" />
                    <div className="h-4 bg-muted animate-pulse rounded-lg w-1/2" />
                    <div className="h-4 bg-muted animate-pulse rounded-lg w-2/3" />
                  </div>
                </div>
              </motion.div>
            ) : // Artifacts data is available
            artifacts?.length > 0 ? (
              <ArtifactTabs />
            ) : (
              messages &&
              Array.isArray(Object.values(messages)[0]) &&
              (Object.values(messages)[0] as Message[]).length > 0 && (
                // No artifacts
                <div className="flex flex-col items-center justify-center gap-2 py-8 text-muted-foreground">
                  <FileSpreadsheet className="w-8 h-8" />
                  <p>{t("selectTheAnalysisAtTheBottomOfTheMessageToViewIt")}</p>
                </div>
              )
            ))}
        </AnimatePresence>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">
              {selectedDatabase ? t("addTables") : t("createDatabase")}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            <Input
              value={databaseName}
              onChange={(e) => setDatabaseName(e.target.value)}
              placeholder={t("databaseName")}
              className="h-9"
              disabled={selectedDatabase}
            />

            <div className="grid w-full items-center gap-4">
              <Input
                type="file"
                accept=".csv"
                multiple
                onChange={handleFileChange}
                className="cursor-pointer file:bg-transparent"
              />

              {csvFiles.length > 0 && (
                <>
                  <div className="flex flex-wrap gap-2">
                    {csvFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-1 bg-muted px-3 py-1 rounded-md text-xs"
                      >
                        <span className="max-w-[150px] truncate">
                          {file.name}
                        </span>
                        <button
                          onClick={() => removeFile(index)}
                          className="ml-1 hover:bg-muted-foreground/20 rounded-full p-1"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {isSubmitting ? (
              <div className="flex items-center justify-center">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
                <span className="ml-2 text-sm text-muted-foreground">
                  {t("processing")}
                </span>
              </div>
            ) : (
              <Button
                variant="default"
                className="h-9 px-4 text-sm font-medium"
                onClick={() => {
                  if (selectedDatabase?.uid) {
                    handleSubmitCSV();
                  } else {
                    handleSubmitDB();
                  }
                }}
                disabled={
                  !databaseName ||
                  csvFiles.length === 0 ||
                  isSubmitting ||
                  isUploading
                }
              >
                {selectedDatabase ? t("addTables") : t("createDatabase")}
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
