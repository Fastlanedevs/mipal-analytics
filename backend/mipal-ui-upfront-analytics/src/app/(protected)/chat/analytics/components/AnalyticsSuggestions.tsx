import { Info, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  SuggestionContent,
  useGetRecommendationsQuery,
} from "@/store/services/intentApi";
import { useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { setSelectedSuggestion } from "@/store/slices/intentsSlice";
import { useEffect, useState } from "react";
import { useGetConversationQuery } from "@/store/services/chatApi";
import { useAppSelector } from "@/store/hooks";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";

const SuggestionCard: React.FC<{
  suggestion: SuggestionContent;
  onClick: () => void;
}> = ({ suggestion, onClick }) => {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        className="relative flex-col items-start gap-2 w-full justify-start h-auto p-4 group bg-accent/30 hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl overflow-hidden"
        onClick={onClick}
      >
        <div className="flex justify-between items-start w-full">
          <div className="flex-1">
            <div className="flex items-start justify-between gap-2">
              <p className="text-[0.85rem] font-medium text-muted-foreground text-left mt-1 text-wrap">
                {suggestion.question}
              </p>
              <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="ghost"
                    className="h-auto p-0 hover:bg-transparent"
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={() => setIsPopoverOpen(true)}
                    onMouseLeave={() => setIsPopoverOpen(false)}
                  >
                    <Info className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className="w-80"
                  onMouseEnter={() => setIsPopoverOpen(true)}
                  onMouseLeave={() => setIsPopoverOpen(false)}
                  align="end"
                >
                  <p className="text-sm text-muted-foreground">
                    {suggestion.explanation}
                  </p>
                </PopoverContent>
              </Popover>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs bg-primary/10 text-primary">
                {suggestion.title}
              </span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs bg-primary/10 text-primary">
                {suggestion.category}
              </span>
            </div>
          </div>
        </div>
      </Button>
    </div>
  );
};

export const AnalyticsSuggestions: React.FC = () => {
  const t = useTranslations("chatPage.analyticsPal.analyticsSuggestions");
  const dispatch = useDispatch();
  const params = useParams();
  const { activeConversationId } = useAppSelector(
    (state: RootState) => state.chat
  );
  const chatId = params?.id as string;
  const { data: conversation, isLoading } = useGetConversationQuery(chatId, {
    skip: !activeConversationId,
  });
  const { selectedDatabase, selectedTable } = useAppSelector(
    (state: RootState) => state.analytics
  );

  const { selectedSuggestion } = useAppSelector(
    (state: RootState) => state.intents
  );

  const messages = useAppSelector((state: RootState) => state.chat.messages);

  const {
    data: recommendations,
    isLoading: isRecommendationsLoading,
    isFetching: isRecommendationsFetching,
    refetch,
  } = useGetRecommendationsQuery(
    {
      database_uid: selectedDatabase?.uid,
      table_uid: selectedTable?.uid,
      count: 5,
    },
    {
      skip:
        !!conversation?.id ||
        !selectedDatabase?.uid ||
        (selectedDatabase?.type !== "postgres" && !selectedTable?.uid),
    }
  );

  useEffect(() => {
    if (
      selectedDatabase?.uid &&
      (selectedDatabase.type === "postgres" || selectedTable?.uid) &&
      !conversation?.id
    ) {
      refetch();
    }
  }, [selectedDatabase, selectedTable]);

  // If there is a conversation or messages, don't show the suggestions
  if (conversation?.id || (messages && Object.values(messages).length > 0)) {
    return null;
  }

  // Pass the first suggestion to the cards component
  return (
    <div className="flex flex-col gap-2 pb-8">
      <div className="flex flex-row items-center gap-2">
        <h3 className="text-lg font-semibold">{t("suggestions")}</h3>
        <div className="h-[1px] flex-1 bg-foreground/30 dark:bg-foreground/90"></div>
      </div>
      <p className="text-sm text-muted-foreground mb-1">
        {t(
          "aiPoweredAnalyticsSuggestionsToHelpYouExploreAndVisualizeYourDataEffectively"
        )}
      </p>
      <div className="space-y-3">
        {/* If no database or table is selected, show a message */}
        {selectedDatabase?.type === "postgres" || selectedTable ? (
          // If loading, show a loading message
          isRecommendationsLoading || isRecommendationsFetching ? (
            // Skeleton loader that matches SuggestionCard structure
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`flex-col items-start gap-2 w-full p-4 bg-accent/30 border border-border rounded-2xl ${
                    i === 1
                      ? "opacity-100"
                      : i === 2
                        ? "opacity-50"
                        : "opacity-30"
                  }`}
                >
                  <div className="flex justify-between items-start w-full">
                    <div className="flex-1 space-y-2">
                      {/* Query text skeleton */}
                      <div className="h-4 bg-muted-foreground/20 rounded animate-pulse w-3/4" />
                      <div className="h-4 bg-muted-foreground/20 rounded animate-pulse w-1/2" />

                      {/* Tags skeleton */}
                      <div className="flex flex-wrap gap-2 mt-2">
                        <div className="h-5 w-20 bg-primary/10 rounded-full animate-pulse" />
                        <div className="h-5 w-16 bg-primary/10 rounded-full animate-pulse" />
                      </div>
                    </div>
                    {/* Info icon skeleton */}
                    <div className="h-4 w-4 bg-muted-foreground/20 rounded-full animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // If there are recommendations, show the recommendations
            recommendations?.recommendations.map(
              (recommendation: SuggestionContent, index) => (
                <SuggestionCard
                  key={index}
                  suggestion={recommendation}
                  onClick={() => {
                    dispatch(setSelectedSuggestion(recommendation));
                    /* Handle suggestion click */
                  }}
                />
              )
            )
          )
        ) : (
          // If no database or table is selected, show a message
          <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed rounded-xl border-muted-foreground/50 bg-accent/10">
            <MessageSquare className="w-8 h-8 mb-2 text-muted-foreground" />
            <h4 className="font-semibold mb-1">
              {t("noSuggestionsAvailable")}
            </h4>
            <p className="text-sm text-muted-foreground">
              {t("pleaseSelectADatabaseAndOrTableToViewAI")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
