"use client";
import { useState, useEffect } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import {
  FileText,
  FileType,
  Search,
  MessageSquare,
  SquareArrowOutUpRight,
  FileCode,
  FileVideo,
  FileAudio,
  FileArchive,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { SearchResponse } from "../chat/types/files";
import {
  useGetPrefixResultsQuery,
  useGetFullSearchResultsQuery,
  useLazyGetFullSearchResultsQuery,
} from "@/store/services/filesApi";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { addSelectedFile } from "@/store/slices/fileSearchSlice";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";

import { useTranslations } from "next-intl";

const Page = () => {
  const t = useTranslations("search");
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchSuggestions, setSearchSuggestions] = useState<
    SearchResponse[] | null
  >(null);
  const [searchResults, setSearchResults] = useState<SearchResponse[] | null>(
    null
  );
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);

  const debouncedSearch = useDebounce(searchQuery, 300);

  const router = useRouter();
  const dispatch = useAppDispatch();

  // RTK Query hooks
  const {
    data: prefixResults,
    isLoading: isPrefixResultsLoading,
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

  const [triggerSearch, { isFetching: isFullFetching }] =
    useLazyGetFullSearchResultsQuery();

  useEffect(() => {
    if (tourGuideState && !tourGuideState.search) {
      startTour("search");
    }
  }, [startTour, tourGuideState]);

  useEffect(() => {
    if (prefixResults && showSuggestions) {
      setSearchSuggestions(prefixResults);
    }
  }, [prefixResults, showSuggestions]);

  useEffect(() => {
    if (initialSearchResults) {
      setSearchResults(initialSearchResults);
    }
  }, [initialSearchResults]);

  const handleSearch = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchQuery !== "") {
      if (
        selectedSuggestionIndex >= 0 &&
        searchSuggestions?.[selectedSuggestionIndex] &&
        searchSuggestions
      ) {
        const suggestion = searchSuggestions[selectedSuggestionIndex];
        setShowSuggestions(false);
        setSearchSuggestions(null);
        setSearchQuery(suggestion.title);
        const { data } = await triggerSearch(suggestion.title);
        if (data) {
          setSearchResults(data);
        }
      } else {
        setShowSuggestions(false);
        setSearchSuggestions(null);
        setSearchResults(null);
        const { data } = await triggerSearch(searchQuery);
        if (data) {
          setSearchResults(data);
        }
      }
      setSelectedSuggestionIndex(-1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (searchSuggestions && searchSuggestions.length > 0) {
        setSelectedSuggestionIndex((prev) =>
          prev < searchSuggestions.length - 1 ? prev + 1 : prev
        );
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedSuggestionIndex((prev) => (prev > -1 ? prev - 1 : prev));
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
    } else if (searchQuery !== "") {
      setShowSuggestions(true);
      setSelectedSuggestionIndex(-1);
    }
  };



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
    // TODO: Implement modal view logic
    window.open(documentAddress, "_blank");
  };

  const handleChatWithDocument = (
    documentId: string,
    title: string,
    address: string,
    content: string
  ) => {
    dispatch(addSelectedFile({ id: documentId, title, address, content }));
    router.push("/home");
  };

  return (
    <div className="p-4 sm:p-6 mx-auto max-w-7xl h-full search-input">
      <div>
        <PageHeader
          title={t("title")}
          description={t("description")}
          className="mb-4 sm:mb-8"
        />

        <div className="mb-4 sm:mb-8">
          <div className="relative max-w-2xl mx-auto web-search-input">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder={t("placeholder")}
              value={searchQuery}
              onChange={async (e) => {
                setSearchQuery(e.target.value);
                if (e.target.value === "") {
                  setShowSuggestions(false);
                  const { data } = await triggerSearch("");
                  if (data) {
                    setSearchResults(data);
                  }
                }
              }}
              onKeyDown={handleSearch}
              className="w-full pl-10 pr-10 h-12 bg-background border-border rounded-xl"
              onFocus={() => setShowSuggestions(true)}
              // onBlur={() => {
              //   setTimeout(() => setShowSuggestions(false), 200);
              // }}
            />
            {(isFullFetching || isInitialFetching) && (
              <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                <LoadingSpinner size={18} />
              </div>
            )}

            {showSuggestions && searchQuery && (
              <div className="absolute w-full mt-1 bg-background border border-border rounded-xl shadow-lg">
                <ul className="py-4 px-2">
                  <p className="text-sm text-muted-foreground pb-1 px-4 flex justify-between">
                    {t("suggestionsFor", { searchQuery })}
                    {(isPrefixResultsLoading || isPrefixFetching) && (
                      <LoadingSpinner size={16} />
                    )}
                  </p>
                  <div className="px-3 py-1">
                    <div className="h-[1px] bg-border" />
                  </div>
                  {searchSuggestions && searchSuggestions.length > 0
                    ? searchSuggestions.map((suggestion, index) => (
                        <li
                          key={index}
                          className={cn(
                            "py-2 px-4 hover:bg-muted cursor-pointer text-sm rounded-md",
                            selectedSuggestionIndex === index && "bg-muted"
                          )}
                          onClick={async (e) => {
                            setShowSuggestions(false);
                            setSearchSuggestions(null);
                            setSearchQuery(suggestion.title);
                            const { data } = await triggerSearch(
                              suggestion.title
                            );
                            if (data) {
                              setSearchResults(data);
                            }
                          }}
                        >
                          {suggestion.title}
                        </li>
                      ))
                    : !(isPrefixResultsLoading || isPrefixFetching) && (
                        <li className="py-2 px-4 text-sm rounded-md">
                          {t("noResultsFound")}
                        </li>
                      )}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="pb-4 sm:pb-8">
        <div className="space-y-3 sm:space-y-4 max-w-2xl mx-auto">
          {searchResults && searchResults.length > 0 ? (
            searchResults.map((result: SearchResponse) => (
              <Card
                key={result.id}
                className="p-3 sm:p-4 hover:shadow-md transition-all duration-200 group cursor-pointer"
              >
                <div className="flex flex-col sm:flex-row justify-between gap-3">
                  <div className="flex flex-col justify-start items-start flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-2 w-full">
                      {getFileIcon(result.title, result.address)}
                      <div className="max-w-[calc(100%-32px)]">
                        <h2 className="text-sm sm:text-base font-medium group-hover:text-primary transition-colors break-words line-clamp-2">
                          {result.title}
                        </h2>
                      </div>
                    </div>
                    <p
                      className={cn(
                        "text-xs sm:text-sm text-muted-foreground whitespace-pre-wrap line-clamp-2 w-full",
                        "group-hover:text-foreground/80 transition-colors"
                      )}
                    >
                      {result.content}
                    </p>
                  </div>
                  <div className="flex flex-row sm:flex-col gap-2 justify-start items-stretch sm:items-end sm:opacity-0 group-hover:opacity-100 transition-all duration-200 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-[120px] text-sm"
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
                      className="w-[120px] text-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleChatWithDocument(
                          result.id,
                          result.title,
                          result.address,
                          ""
                        );
                      }}
                    >
                      <MessageSquare className="w-4 h-4 mr-2" />
                      {t("attach")}
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                {searchResults?.length === 0 ? t("noResultsFound") : ""}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Page;
