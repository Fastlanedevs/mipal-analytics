"use client";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  FileText,
  Search,
  SquareArrowOutUpRight,
  MessageSquare,
  MessageSquareOff,
  FileType,
  FileCode,
  FileVideo,
  FileAudio,
  FileArchive,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  removeSelectedFile,
  addSelectedFile,
  SelectedFile,
} from "@/store/slices/fileSearchSlice";
import { useDebounce } from "@/hooks/useDebounce";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { cn } from "@/lib/utils";
import {
  useGetPrefixResultsQuery,
  useLazyGetFullSearchResultsQuery,
  useGetFullSearchResultsQuery,
} from "@/store/services/filesApi";
import { SearchResponse } from "@/app/(protected)/chat/types/chat";
import {
  GoogleDocsIcon,
  GoogleSheetsIcon,
  GoogleSlidesIcon,
  GoogleDrawingsIcon,
  GooglePDFIcon,
} from "@/components/icons/GoogleDriveIcons";
import { useTranslations } from "next-intl";
interface SearchModalProps {
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
}

export const SearchModal = ({
  isSearchOpen,
  setIsSearchOpen,
}: SearchModalProps) => {
  const t = useTranslations("chatPage.searchModal");
  const dialogRef = React.useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const dispatch = useAppDispatch();
  const selectedFiles = useAppSelector(
    (state) => state.fileSearch.selectedFiles
  );
  const debouncedSearch = useDebounce(searchQuery, 300);

  const {
    data: prefixResults,
    isLoading: isPrefixLoading,
    isFetching: isPrefixFetching,
  } = useGetPrefixResultsQuery(debouncedSearch, {
    skip: !debouncedSearch,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
  });

  const { data: initialSearchResults, isFetching: isInitialFetching } =
    useGetFullSearchResultsQuery("", {
      refetchOnMountOrArgChange: true,
    });

  const [
    triggerFullSearch,
    { data: fullSearchResults, isFetching: isFullFetching },
  ] = useLazyGetFullSearchResultsQuery();

  const [showSuggestions, setShowSuggestions] = useState(true);
  const [searchSuggestions, setSearchSuggestions] = useState<SearchResponse[]>(
    []
  );

  // Add state for selected suggestion index
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);

  // Add effect to update suggestions
  React.useEffect(() => {
    if (prefixResults && showSuggestions) {
      setSearchSuggestions(prefixResults as unknown as SearchResponse[]);
    }
  }, [prefixResults, showSuggestions]);

  const handleSearch = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchQuery !== "") {
      if (
        showSuggestions &&
        selectedSuggestionIndex >= 0 &&
        searchSuggestions
      ) {
        // If suggestion is selected, use that suggestion
        const selectedSuggestion = searchSuggestions[selectedSuggestionIndex];
        setShowSuggestions(false);
        setSearchSuggestions([]);
        setSearchQuery(selectedSuggestion.title);
        await triggerFullSearch(selectedSuggestion.title);
      } else {
        // Normal search behavior
        setShowSuggestions(false);
        setSearchSuggestions([]);
        await triggerFullSearch(searchQuery);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (searchSuggestions && showSuggestions) {
        setSelectedSuggestionIndex((prev) =>
          prev < searchSuggestions.length - 1 ? prev + 1 : prev
        );
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (showSuggestions) {
        setSelectedSuggestionIndex((prev) => (prev > -1 ? prev - 1 : -1));
      }
    } else if (searchQuery !== "") {
      setShowSuggestions(true);
      setSelectedSuggestionIndex(-1);
    }
  };

  const getFileIcon = (title: string, address?: string) => {
    // Check if it's a Google Drive URL
    if (address?.includes("docs.google.com")) {
      if (address.includes("/document/d/")) {
        return <GoogleDocsIcon className="w-4 h-4" />;
      } else if (address.includes("/spreadsheets/d/")) {
        return <GoogleSheetsIcon className="w-4 h-4" />;
      } else if (address.includes("/presentation/d/")) {
        return <GoogleSlidesIcon className="w-4 h-4" />;
      } else if (address.includes("/drawing/d/")) {
        return <GoogleDrawingsIcon className="w-4 h-4" />;
      } else if (address.includes("/script/d/")) {
        return <FileCode className="w-4 h-4 text-yellow-500" />;
      } else if (address.includes("/video/d/")) {
        return <FileVideo className="w-4 h-4 text-red-500" />;
      } else if (address.includes("/audio/d/")) {
        return <FileAudio className="w-4 h-4 text-pink-500" />;
      } else if (address.includes("/archive/d/")) {
        return <FileArchive className="w-4 h-4 text-gray-500" />;
      }
    }

    // Handle other file types
    const extension = title.split(".").pop()?.toLowerCase();
    switch (extension) {
      case "pdf":
        return <GooglePDFIcon className="w-4 h-4" />;
      case "csv":
        return <GoogleDocsIcon className="w-4 h-4" />;
      case "doc":
      case "docx":
        return <FileText className="w-4 h-4 text-blue-500" />;
      default:
        return <FileType className="w-4 h-4 text-gray-500" />;
    }
  };

  const handleViewDocument = (documentAddress: string) => {
    window.open(documentAddress, "_blank");
  };

  const handleChatWithDocument = (
    documentId: string,
    title: string,
    address: string,
    content: string
  ) => {
    // setIsSearchOpen(false);
    dispatch(addSelectedFile({ id: documentId, title, address, content }));
  };

  const [displayResults, setDisplayResults] = useState<SearchResponse[]>([]);

  // Update the click outside handler
  useEffect(() => {
    // setSearchQuery("");
    // setSearchSuggestions(null);
    // setShowSuggestions(false);
    const handleClickOutside = (event: MouseEvent) => {
      // Check if click is on backdrop (the semi-transparent overlay)
      const target = event.target as HTMLElement;
      if (target.classList.contains("modal-backdrop")) {
        setIsSearchOpen(false);
      }
    };

    if (isSearchOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    // Reset the search query
    if (
      !isSearchOpen &&
      (displayResults.length > 0 ||
        searchSuggestions?.length > 0 ||
        searchQuery !== "")
    ) {
      setDisplayResults([]);
      setSearchSuggestions([]);
      setShowSuggestions(false);
      setSearchQuery("");
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isSearchOpen]);

  useEffect(() => {
    if (fullSearchResults) {
      setDisplayResults(fullSearchResults as unknown as SearchResponse[]);
    }
  }, [fullSearchResults]);

  useEffect(() => {
    if (initialSearchResults) {
      setDisplayResults(initialSearchResults as unknown as SearchResponse[]);
    }
  }, [initialSearchResults]);

  // if the search query is empty, set the display results to an empty array
  // if (searchQuery === "") {
  //   displayResults = [];
  // }

  const isFileSelected = (fileId: string) => {
    return selectedFiles.some((file: SelectedFile) => file.id === fileId);
  };

  return (
    <>
      {
        <div
          className={`fixed inset-0 z-[100] flex items-center justify-center ${
            isSearchOpen ? "block" : "hidden"
          }`}
        >
          {/* Add modal-backdrop class to the backdrop */}
          <div className="fixed inset-0 bg-black/10 modal-backdrop" />

          {/* Modal content */}
          <div
            ref={dialogRef}
            className="relative bg-white dark:bg-zinc-900 rounded-2xl shadow-sm w-full max-w-[900px] mx-4 max-h-[90vh] h-[90%] overflow-hidden animate-fade-down animate-ease-out animate-duration-300 border"
          >
            <div className="p-4 sm:p-6 flex flex-col h-full max-h-[90vh]">
              {/* Header */}
              <div className="flex items-center justify-between shrink-0 px-2">
                <h2 className="text-base sm:text-lg font-semibold flex items-center gap-3">
                  {t("searchDocuments")}
                </h2>
                <button
                  onClick={() => setIsSearchOpen(false)}
                  className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <svg
                    className="w-4 h-4 sm:w-5 sm:h-5 text-gray-500 dark:text-gray-400"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>

              {/* Search Input */}
              <div className="relative mt-4 shrink-0 px-2">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground dark:text-gray-400" />
                <input
                  type="text"
                  placeholder={t("searchDocumentsPlaceholder")}
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    if (e.target.value === "") {
                      setShowSuggestions(false);
                      triggerFullSearch("");
                    }
                  }}
                  onKeyDown={handleSearch}
                  onFocus={() => setShowSuggestions(true)}
                  // onBlur={() => {
                  //   setTimeout(() => setShowSuggestions(false), 200);
                  // }}
                  className="w-full pl-10 h-12 bg-background border rounded-xl dark:bg-zinc-800/50 dark:border-zinc-700/50 focus:outline-none dark:focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-primary/30 dark:text-gray-100 dark:placeholder:text-gray-400 transition-colors"
                />
                {(isFullFetching || isInitialFetching) && (
                  <div className="absolute right-6 top-1/2 transform -translate-y-1/2">
                    <LoadingSpinner size={18} />
                  </div>
                )}

                {showSuggestions && searchQuery && (
                  <div className="absolute left-[6px] right-[6px] mt-1 bg-background border border-border rounded-xl shadow-lg dark:bg-zinc-800/50 dark:border-zinc-700/50 z-10">
                    <ul className="py-4 px-2 max-h-[300px] overflow-y-auto">
                      <p className="text-sm text-muted-foreground pb-1 px-4 flex justify-between dark:text-gray-400">
                        {t("suggestionsFor", { searchQuery })}
                        {(isPrefixLoading || isPrefixFetching) && (
                          <LoadingSpinner size={16} />
                        )}
                      </p>
                      <div className="px-3 py-1">
                        <div className="h-[1px] bg-border dark:bg-zinc-700" />
                      </div>
                      {searchSuggestions && searchSuggestions.length > 0
                        ? searchSuggestions.map((suggestion, index) => (
                            <li
                              key={index}
                              className={cn(
                                "py-2 px-4 hover:bg-muted cursor-pointer text-sm rounded-md dark:hover:bg-zinc-700/50 dark:text-gray-100",
                                selectedSuggestionIndex === index &&
                                  "bg-muted dark:bg-zinc-700/50"
                              )}
                              onClick={async () => {
                                setShowSuggestions(false);
                                setSearchSuggestions([]);
                                setSearchQuery(suggestion.title);
                                await triggerFullSearch(suggestion.title);
                              }}
                            >
                              {suggestion.title}
                            </li>
                          ))
                        : !(isPrefixLoading || isPrefixFetching) && (
                            <li className="py-2 px-4 text-sm rounded-md dark:text-gray-100">
                              {t("noResultsFound")}
                            </li>
                          )}
                    </ul>
                  </div>
                )}
              </div>

              {/* Results */}
              <div className="mt-4 overflow-y-auto flex-grow space-y-4 min-h-0 p-2 relative">
                {!isFullFetching &&
                displayResults &&
                displayResults.length > 0 ? (
                  displayResults.map((result) => (
                    <Card
                      key={result.id}
                      className="p-4 hover:shadow-md transition-all duration-200 group cursor-pointer flex flex-col md:flex-row justify-between gap-4 dark:bg-zinc-800/50 dark:border-zinc-700/50 w-full"
                      onClick={() => window.open(result.address, "_blank")}
                    >
                      <div className="flex flex-col justify-start items-start w-full">
                        <div className="flex items-center gap-2 mb-2">
                          {getFileIcon(result.title, result.address)}
                          <h2 className="text-base font-medium group-hover:text-primary transition-colors dark:text-gray-100">
                            {result.title}
                          </h2>
                        </div>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-2 group-hover:text-foreground/80 transition-colors dark:text-gray-400 w-full">
                          {result.content}
                        </p>
                      </div>
                      <div className="flex gap-2 justify-start items-end md:flex-col md:opacity-0 group-hover:opacity-100 transition-all duration-200">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 md:flex-none md:w-[100px] dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewDocument(result.address);
                          }}
                        >
                          <SquareArrowOutUpRight className="w-4 h-4 mr-2" />
                          {t("open")}
                        </Button>
                        <Button
                          size="sm"
                          className={cn(
                            "flex-1 md:flex-none md:w-[100px]",
                            isFileSelected(result.id) && "bg-red-500"
                          )}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (isFileSelected(result.id)) {
                              dispatch(removeSelectedFile(result.id));
                            } else {
                              handleChatWithDocument(
                                result.id,
                                result.title,
                                result.address,
                                result.content
                              );
                            }
                          }}
                          // variant={isFileSelected(result.id) ? "secondary" : "default"}
                          // disabled={isFileSelected(result.id)}
                        >
                          {isFileSelected(result.id) ? (
                            <MessageSquareOff className="w-4 h-4 mr-2" />
                          ) : (
                            <MessageSquare className="w-4 h-4 mr-2" />
                          )}
                          {isFileSelected(result.id)
                            ? t("detach")
                            : t("attach")}
                        </Button>
                      </div>
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground dark:text-gray-400">
                      {displayResults?.length === 0 ? t("noResultsFound") : ""}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      }
    </>
  );
};
