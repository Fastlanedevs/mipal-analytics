"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetTemplateByIdQuery,
  useGenerateSubsectionQuestionsMutation,
  useGetPromptQuestionsMutation,
  useAcceptQuestionsMutation,
  useDeleteQuestionsMutation,
} from "@/store/services/sourcingApi";
import {
  ChevronRight,
  X,
  ChevronLeft,
  Home,
  FileText,
  Plus,
  Loader2,
  Trash2,
  FileQuestion,
  MessageSquare,
  Sparkles,
  Users,
  PanelRightClose,
  Notebook,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { SimpleChatInput } from "@/app/(protected)/chat/components/SimpleChatInput";
import { Checkbox } from "@/components/ui/checkbox";
import AnswerGenerationSidebar from "./components/AnswerGenerationSidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { MarkdownRenderer } from "@/app/(protected)/chat/components/MarkdownRenderer";
import RfpPreview from "./components/RfpPreview";

interface Question {
  question_id: string;
  question_name: string;
  is_accepted: boolean;
  answer?: string;
  accepted_answer?: boolean;
  sources?: {
    file_id: string;
    file_name: string;
    file_url: string;
    confidence_score?: number;
    score?: number;
  }[];
}

interface Subsection {
  subheading: string;
  subsection_id: string;
  questions: Question[];
}

interface Section {
  heading: string;
  subsections: Subsection[];
  section_id: string;
}

export default function CreateRFPPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateId = searchParams.get("template_id");

  // Function to determine color class based on confidence score
  const getConfidenceColorClass = (score: number) => {
    if (score >= 0.7) return "bg-green-500";
    if (score >= 0.5) return "bg-amber-500";
    return "bg-red-500";
  };

  const {
    data: templateDetails,
    isLoading: isLoadingTemplate,
    error: templateError,
    refetch: refetchTemplate,
  } = useGetTemplateByIdQuery(templateId as string, {
    skip: !templateId,
  });

  const handleDocumentUploaded = () => {
    refetchTemplate();
  };

  const [getPromptQuestions] = useGetPromptQuestionsMutation();
  const [generateSubsectionQuestions] =
    useGenerateSubsectionQuestionsMutation();
  const [acceptQuestions] = useAcceptQuestionsMutation();
  const [deleteQuestions] = useDeleteQuestionsMutation();
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [selectedSubsection, setSelectedSubsection] = useState<string | null>(
    null
  );
  const [selectedSubsectionId, setSelectedSubsectionId] = useState<
    string | null
  >(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [width, setWidth] = useState(window.innerWidth * 0.5);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(width);
  const [chatMessage, setChatMessage] = useState("");
  const [selectedQuestions, setSelectedQuestions] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAnswerSidebarOpen, setIsAnswerSidebarOpen] = useState(false);
  const [isNoteSidebarOpen, setIsNoteSidebarOpen] = useState(false);
  const [answerSidebarWidth, setAnswerSidebarWidth] = useState(
    window.innerWidth * 0.6
  );
  const [noteSidebarWidth, setNoteSidebarWidth] = useState(
    window.innerWidth * 0.6
  );
  const [isAnswerSidebarResizing, setIsAnswerSidebarResizing] = useState(false);
  const [isNoteSidebarResizing, setIsNoteSidebarResizing] = useState(false);
  const [answerStartX, setAnswerStartX] = useState(0);
  const [noteStartX, setNoteStartX] = useState(0);
  const [answerStartWidth, setAnswerStartWidth] = useState(answerSidebarWidth);
  const [noteStartWidth, setNoteStartWidth] = useState(noteSidebarWidth);
  const [isGeneratingFromPrompt, setIsGeneratingFromPrompt] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const streamRef = useRef<AbortController | null>(null);
  console.log("questions", questions);
  // const [generatePreview, { isLoading: isGeneratingPreview }] = useGeneratePreviewMutation();

  const handleSubsectionClick = async (
    sectionHeading: string,
    subsectionHeading: string,
    subsectionId: string,
    questions: Question[]
  ) => {
    setSelectedSection(sectionHeading);
    setSelectedSubsection(subsectionHeading);
    setSelectedSubsectionId(subsectionId);
    setIsLoadingQuestions(true);
    setQuestions([]);

    try {
      if (questions.length === 0) {
        const response = await generateSubsectionQuestions({
          templateId: templateId as string,
          subsectionId: subsectionId,
        }).unwrap();

        if (response?.questions) {
          setQuestions(response.questions);
          const acceptedQuestionIds = response.questions
            .filter((q: Question) => q.is_accepted)
            .map((q: Question) => q.question_id);
          setSelectedQuestions(acceptedQuestionIds);
          await refetchTemplate();
        }
      } else {
        const subsection = templateDetails?.sections
          .flatMap((section: Section) => section.subsections)
          .find((sub: Subsection) => sub.subsection_id === subsectionId);

        const fetchedQuestions = subsection?.questions || [];
        setQuestions(fetchedQuestions);
        const acceptedQuestionIds = fetchedQuestions
          .filter((q: Question) => q.is_accepted)
          .map((q: Question) => q.question_id);
        setSelectedQuestions(acceptedQuestionIds);
      }
    } catch (error) {
      console.error("Error in handleSubsectionClick:", error);
      toast({
        title: "Failed to load questions. Please try again.",
        variant: "destructive",
      });
      setQuestions([]);
      setSelectedQuestions([]);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    setStartX(e.pageX);
    setStartWidth(width);
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startX - e.pageX;
      const windowWidth = window.innerWidth;
      const minWidth = windowWidth * 0.2; // 20% of window width
      const maxWidth = windowWidth * 0.5; // 50% of window width
      const newWidth = Math.min(
        Math.max(minWidth, startWidth + diff),
        maxWidth
      );
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, startX, startWidth]);

  useEffect(() => {
    if (templateError) {
      toast({
        title: "Failed to load template. Please try again.",
        variant: "destructive",
      });
    }
  }, [templateError]);

  const handleSendMessage = async (content: string) => {
    if (!selectedSubsectionId) return;

    try {
      setIsGeneratingFromPrompt(true);
      const response = await getPromptQuestions({
        subsectionId: selectedSubsectionId,
        prompt: content,
      }).unwrap();

      setQuestions(response.questions);
      const acceptedQuestionIds = response.questions
        .filter((q: Question) => q.is_accepted)
        .map((q: Question) => q.question_id);
      setSelectedQuestions(acceptedQuestionIds);
      setChatMessage("");
      await refetchTemplate(); // Refetch template to update questions
    } catch (error) {
      console.error("Error getting prompt questions:", error);
      toast({
        title: "Failed to get questions from prompt. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingFromPrompt(false);
    }
  };

  const handleQuestionSelect = (questionId: string) => {
    setSelectedQuestions((prev) => {
      if (prev.includes(questionId)) {
        return prev.filter((id) => id !== questionId);
      } else {
        return [...prev, questionId];
      }
    });
  };

  const handleAcceptQuestions = async () => {
    if (!templateId || !selectedSubsectionId || selectedQuestions.length === 0)
      return;

    try {
      setIsProcessing(true);
      await acceptQuestions({
        templateId,
        subsectionId: selectedSubsectionId,
        questionIds: selectedQuestions,
      }).unwrap();

      setIsAnswerSidebarOpen(false);
      setSelectedSection(null);
      setSelectedSubsection(null);
      setSelectedSubsectionId(null);
      setQuestions([]);
      setSelectedQuestions([]);
      await refetchTemplate(); // Refetch template to update questions
      // toast.success("Questions accepted successfully");
      toast({
        title: "Questions accepted successfully",
        description: "Questions accepted successfully",
      });
    } catch (error) {
      console.error("Error accepting questions:", error);
      toast({
        title: "Failed to accept questions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteSingleQuestion = async (questionId: string) => {
    if (!templateId || !selectedSubsectionId) return;

    try {
      setIsProcessing(true);
      await deleteQuestions({
        templateId: templateId,
        subsectionId: selectedSubsectionId,
        questionIds: [questionId],
      }).unwrap();

      // Remove the deleted question from the local state
      setQuestions((prev) =>
        prev.filter((q: Question) => q.question_id !== questionId)
      );
      setSelectedQuestions((prev) => prev.filter((id) => id !== questionId));

      await refetchTemplate(); // Refetch template to update questions
      toast({
        title: "Question deleted successfully",
      });
    } catch (error) {
      console.error("Error deleting question:", error);
      toast({
        title: "Failed to delete question. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAnswerSidebarMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsAnswerSidebarResizing(true);
    setAnswerStartX(e.pageX);
    setAnswerStartWidth(answerSidebarWidth);
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  const handleNoteSidebarMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsNoteSidebarResizing(true);
    setNoteStartX(e.pageX);
    setNoteStartWidth(noteSidebarWidth);
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isAnswerSidebarResizing) {
        const diff = answerStartX - e.pageX;
        const windowWidth = window.innerWidth;
        const minWidth = windowWidth * 0.2;
        const maxWidth = windowWidth * 0.5;
        const newWidth = Math.min(
          Math.max(minWidth, answerStartWidth + diff),
          maxWidth
        );
        setAnswerSidebarWidth(newWidth);
      } else if (isNoteSidebarResizing) {
        const diff = noteStartX - e.pageX;
        const windowWidth = window.innerWidth;
        const minWidth = windowWidth * 0.2;
        const maxWidth = windowWidth * 0.5;
        const newWidth = Math.min(
          Math.max(minWidth, noteStartWidth + diff),
          maxWidth
        );
        setNoteSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsAnswerSidebarResizing(false);
      setIsNoteSidebarResizing(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    if (isAnswerSidebarResizing || isNoteSidebarResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [
    isAnswerSidebarResizing,
    isNoteSidebarResizing,
    answerStartX,
    noteStartX,
    answerStartWidth,
    noteStartWidth,
  ]);

  if (isLoadingTemplate) {
    return (
      <div className="flex h-full">
        <div className="flex-1 overflow-y-auto">
          <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
            <div className="flex flex-col items-start justify-center py-8 space-y-8">
              {/* Breadcrumb and Back Button Skeleton */}
              <div className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-md" />
                <div className="flex items-center gap-2 text-sm">
                  <Skeleton className="h-8 w-20" />
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <Skeleton className="h-8 w-24" />
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <Skeleton className="h-8 w-32" />
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <Skeleton className="h-8 w-24" />
                </div>
              </div>

              {/* Page Header Skeleton */}
              <div className="flex flex-col gap-1 w-full">
                <div className="flex justify-between items-center w-full">
                  <Skeleton className="h-8 w-64" />
                </div>
                <Skeleton className="h-5 w-full max-w-md" />
              </div>

              {/* Sections Skeleton */}
              <div className="space-y-6 w-full">
                <div className="space-y-4">
                  {[1, 2, 3].map((sectionIndex) => (
                    <div
                      key={sectionIndex}
                      className="border rounded-lg overflow-hidden"
                    >
                      {/* Section Header Skeleton */}
                      <div className="bg-muted/50 p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Skeleton className="h-6 w-40" />
                            <Skeleton className="h-5 w-24 ml-2" />
                          </div>
                          <Skeleton className="h-10 w-32" />
                        </div>
                      </div>

                      {/* Subsections Skeleton */}
                      <div className="p-4">
                        <div className="space-y-2">
                          {[1, 2, 3].map((subIndex) => (
                            <div key={subIndex}>
                              <div className="flex items-center justify-between p-3 text-sm rounded-md hover:bg-muted group">
                                <div className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-muted" />
                                  <Skeleton className="h-5 w-48" />
                                </div>
                                <div className="flex items-center gap-2">
                                  <Skeleton className="h-7 w-28" />
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                </div>
                              </div>

                              {/* Show table skeleton for one subsection in each section */}
                              {subIndex === 1 && sectionIndex === 1 && (
                                <div className="mt-4 ml-6">
                                  {/* Column Headers Skeleton */}
                                  <div className="grid grid-cols-[minmax(200px,1fr)_minmax(300px,1.5fr)_minmax(180px,1fr)] border-b border-muted relative">
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 border-r border-muted">
                                      <FileQuestion className="h-4 w-4" />
                                      Question
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 border-r border-muted">
                                      <MessageSquare className="h-4 w-4" />
                                      Answer
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 border-r border-muted">
                                      <FileText className="h-4 w-4" />
                                      Source
                                    </div>
                                    {/* <div className="flex items-center gap-2 text-sm text-muted-foreground p-3">
                                      <Users className="h-4 w-4" />
                                      Collab
                                    </div> */}
                                  </div>

                                  {/* Questions List Skeleton */}
                                  <div className="divide-y border-muted">
                                    {[1, 2].map((qIndex) => (
                                      <div
                                        key={qIndex}
                                        className="grid grid-cols-[minmax(200px,1fr)_minmax(300px,1.5fr)_minmax(180px,1fr)] hover:bg-muted/50 transition-colors relative"
                                      >
                                        {/* Question Name Skeleton */}
                                        <div className="p-3 text-sm border-r border-muted">
                                          <Skeleton className="h-5 w-full" />
                                        </div>

                                        {/* Answer Column Skeleton */}
                                        <div className="p-3 text-sm border-r border-muted">
                                          <Skeleton className="h-5 w-16" />
                                        </div>

                                        {/* Source Column Skeleton */}
                                        <div className="p-3 text-sm border-r border-muted">
                                          <Skeleton className="h-5 w-8" />
                                        </div>

                                        {/* Collab Column Skeleton */}
                                        {/* <div className="p-3 text-sm flex items-center gap-2">
                                          <Skeleton className="h-8 w-24" />
                                        </div> */}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Bottom Buttons Skeleton */}
                <div className="flex justify-end space-x-2">
                  <Skeleton className="h-10 w-24" />
                  <Skeleton className="h-10 w-32" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
          <div className="flex flex-col items-start justify-center py-8 space-y-8">
            {/* Breadcrumb and Back Button */}
            <div className="flex flex-wrap items-center gap-4">
              <Button
                variant="outline"
                size="icon"
                onClick={() => router.back()}
                className="h-10 w-10 hover:bg-accent"
                title="Go back"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 hover:bg-accent"
                  onClick={() => router.push("/")}
                >
                  <Home className="h-4 w-4 mr-1" />
                  <span className="hidden sm:inline">Home</span>
                </Button>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 hover:bg-accent"
                  onClick={() => router.push("/sourcing")}
                >
                  <span className="hidden sm:inline">Sourcing</span>
                  <span className="sm:hidden">S</span>
                </Button>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 hover:bg-accent"
                  onClick={() => router.push("/sourcing/rfp")}
                >
                  <span className="hidden sm:inline">RFP Templates</span>
                  <span className="sm:hidden">RFP</span>
                </Button>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-primary">Create RFP</span>
              </div>
            </div>

            {/* Page Header with Generate Answer Button */}
            <div className="flex flex-col gap-1 w-full">
              <div className="flex justify-between items-center w-full">
                <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  {templateDetails?.name || "Create New RFP"}
                </h1>
              </div>
              <p className="text-sm text-muted-foreground">
                Create and customize your RFP by selecting sections and adding
                questions
              </p>
            </div>

            {/* Rest of the existing content */}
            {templateId && templateDetails ? (
              <div className="space-y-6 w-full">
                <div className="space-y-4">
                  {templateDetails.sections.map((section, index) => (
                    <Card key={index} className="overflow-hidden border">
                      <CardHeader className="bg-muted/50 p-4">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-lg flex items-center gap-2">
                            <span>{section.heading}</span>
                            <Badge
                              variant="secondary"
                              className="md:block hidden ml-2"
                            >
                              {section.subsections.length}{" "}
                              {section.subsections.length === 1
                                ? "subsection"
                                : "subsections"}
                            </Badge>
                          </CardTitle>
                          {/* only show if there is any question in the section */}
                          {section?.subsections?.some((subsection) =>
                            subsection.questions.some(
                              (question) => question.is_accepted
                            )
                          ) && (
                            <Button
                              onClick={() => {
                                setSelectedSection(section.heading);
                                setSelectedQuestion(null);
                                setIsAnswerSidebarOpen(true);
                              }}
                              className="gap-2"
                            >
                              <Sparkles className="h-4 w-4" />
                              Add Answers
                            </Button>
                          )}
                        </div>
                      </CardHeader>
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          {section.subsections.map((subsection, subIndex) => (
                            <div key={subIndex}>
                              <div
                                className={cn(
                                  "flex items-center justify-between p-3 text-sm rounded-md transition-colors  group",
                                  selectedSubsectionId ===
                                    subsection.subsection_id
                                    ? "bg-primary/10 text-primary"
                                    : "hover:bg-muted"
                                )}
                              >
                                <span className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                                  {subsection.subheading}
                                </span>
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleSubsectionClick(
                                        section.heading,
                                        subsection.subheading,
                                        subsection.subsection_id,
                                        subsection.questions
                                      );
                                    }}
                                  >
                                    <Plus className="h-3.5 w-3.5 mr-1" />
                                    <span className="text-xs">
                                      Add Question
                                    </span>
                                  </Button>
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                </div>
                              </div>

                              {/* Show accepted questions for this subsection */}
                              {subsection.questions &&
                                subsection.questions.some(
                                  (question) => question.is_accepted
                                ) && (
                                  <div className="mt-4 ml-6">
                                    <div className="overflow-x-auto -mx-4 sm:mx-0">
                                      <div className="inline-block min-w-full align-middle px-4 sm:px-0">
                                        {/* Column Headers - Show once per subsection */}
                                        <div className="grid grid-cols-[minmax(200px,1fr)_minmax(300px,1.5fr)_minmax(180px,1fr)] border-b border-muted relative">
                                          <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 border-r border-muted">
                                            <FileQuestion className="h-4 w-4" />
                                            <span className="hidden sm:inline">
                                              Question
                                            </span>
                                            <span className="sm:hidden">Q</span>
                                          </div>
                                          <div className="flex items-center gap-2 text-sm text-muted-foreground p-3 border-r border-muted">
                                            <MessageSquare className="h-4 w-4" />
                                            <span className="hidden sm:inline">
                                              Answer
                                            </span>
                                            <span className="sm:hidden">A</span>
                                          </div>
                                          <div className="flex items-center gap-2 text-sm text-muted-foreground p-3  border-muted">
                                            <FileText className="h-4 w-4" />
                                            <span className="hidden sm:inline">
                                              Source
                                            </span>
                                            <span className="sm:hidden">S</span>
                                          </div>
                                          {/* <div className="flex items-center gap-2 text-sm text-muted-foreground p-3">
                                            <Users className="h-4 w-4" />
                                            <span className="hidden sm:inline">
                                              Collab
                                            </span>
                                            <span className="sm:hidden">C</span>
                                          </div> */}
                                        </div>

                                        {/* Questions List */}
                                        <div className="divide-y border-muted">
                                          {subsection.questions
                                            .filter(
                                              (question: Question) =>
                                                question.is_accepted
                                            )
                                            .map((question: Question) => (
                                              <div
                                                key={question.question_id}
                                                className="grid grid-cols-[minmax(200px,1fr)_minmax(300px,1.5fr)_minmax(180px,1fr)] hover:bg-muted/50 transition-colors relative"
                                              >
                                                {/* Name Column */}
                                                <div className="p-3 text-sm border-r border-muted">
                                                  <div className="line-clamp-2">
                                                    {question.question_name}
                                                  </div>
                                                </div>

                                                {/* Answer Column */}
                                                <div className="p-3 text-sm text-muted-foreground border-r border-muted relative group">
                                                  {question.answer &&
                                                  question?.accepted_answer ? (
                                                    <div className="max-h-24 overflow-hidden relative">
                                                      <div className="prose prose-sm dark:prose-invert max-w-none">
                                                        {/* Render markdown content */}
                                                        <MarkdownRenderer
                                                          content={question.answer
                                                            .split("\n")
                                                            .slice(0, 3)
                                                            .join("\n")}
                                                        />
                                                      </div>
                                                      {question.answer.split(
                                                        "\n"
                                                      ).length > 3 && (
                                                        <>
                                                          <div className="absolute bottom-0 left-0 right-0 h-12 " />
                                                          <span
                                                            className="text-xs text-muted-foreground hover:text-primary mt-1 cursor-pointer inline-flex items-center"
                                                            onClick={() => {
                                                              setSelectedQuestion(
                                                                {
                                                                  id: question.question_id,
                                                                  name: question.question_name,
                                                                }
                                                              );
                                                              setIsAnswerSidebarOpen(
                                                                true
                                                              );
                                                            }}
                                                          >
                                                            View more...
                                                          </span>
                                                        </>
                                                      )}
                                                    </div>
                                                  ) : (
                                                    <span>-</span>
                                                  )}
                                                  {/* below md make them visible */}
                                                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2 md:opacity-0 group-hover:opacity-100 bg-muted transition-opacity">
                                                    <TooltipProvider>
                                                      <Tooltip>
                                                        <TooltipTrigger asChild>
                                                          <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 hover:bg-primary/10"
                                                            onClick={() => {
                                                              setSelectedQuestion(
                                                                {
                                                                  id: question.question_id,
                                                                  name: question.question_name,
                                                                }
                                                              );
                                                              setIsAnswerSidebarOpen(
                                                                true
                                                              );
                                                              setSelectedSection(
                                                                section.section_id
                                                              );
                                                            }}
                                                          >
                                                            <PanelRightClose className="h-4 w-4" />
                                                          </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                          <p>
                                                            Open answer sidebar
                                                          </p>
                                                        </TooltipContent>
                                                      </Tooltip>
                                                    </TooltipProvider>

                                                    {/* hide note for now */}
                                                    {/* <TooltipProvider>
                                                      <Tooltip>
                                                        <TooltipTrigger asChild>
                                                          <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 hover:bg-primary/10"
                                                            onClick={() => {
                                                              setSelectedQuestion(
                                                                {
                                                                  id: question.question_id,
                                                                  name: question.question_name,
                                                                }
                                                              );

                                                              setIsNoteSidebarOpen(
                                                                true
                                                              );
                                                            }}
                                                          >
                                                            <Notebook className="h-4 w-4" />
                                                          </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                          <p>Add note</p>
                                                        </TooltipContent>
                                                      </Tooltip>
                                                    </TooltipProvider> */}
                                                  </div>
                                                </div>

                                                {/* Source Column */}
                                                {question.answer &&
                                                question.accepted_answer ? (
                                                  question.sources &&
                                                  question.sources.length >
                                                    0 ? (
                                                    <ul className="p-3 space-y-2.5 list-none">
                                                      {question.sources.map(
                                                        (source) => (
                                                          <li
                                                            key={source.file_id}
                                                            className="text-sm border border-gray-100 dark:border-gray-800 rounded-md p-2 bg-gray-50 dark:bg-gray-900"
                                                          >
                                                            <div className="flex items-start gap-2">
                                                              <FileText className="h-4 w-4 mt-0.5 flex-shrink-0 text-primary" />
                                                              <div className="flex-1 min-w-0">
                                                                <span className="overflow-hidden text-ellipsis whitespace-nowrap font-medium block">
                                                                  {
                                                                    source.file_name
                                                                  }
                                                                </span>
                                                                {(source.confidence_score ||
                                                                  source.score) && (
                                                                  <div className="mt-1.5">
                                                                    <div className="flex items-center justify-between mb-1">
                                                                      <span className="text-xs text-muted-foreground">
                                                                        Confidence:
                                                                      </span>
                                                                      <span className="text-xs font-medium">
                                                                        {Math.round(
                                                                          (source.confidence_score ||
                                                                            source.score ||
                                                                            0) *
                                                                            100
                                                                        )}
                                                                        %
                                                                      </span>
                                                                    </div>
                                                                    <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                                      <div
                                                                        className={`h-full rounded-full ${getConfidenceColorClass(source.confidence_score || source.score || 0)}`}
                                                                        style={{
                                                                          width: `${Math.round((source.confidence_score || source.score || 0) * 100)}%`,
                                                                        }}
                                                                      />
                                                                    </div>
                                                                  </div>
                                                                )}
                                                              </div>
                                                            </div>
                                                          </li>
                                                        )
                                                      )}
                                                    </ul>
                                                  ) : (
                                                    <span className="p-4">
                                                      -
                                                    </span>
                                                  )
                                                ) : (
                                                  <span className="p-4">-</span>
                                                )}
                                              </div>
                                            ))}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="flex justify-end space-x-2">
                  {templateId && <RfpPreview templateId={templateId} />}
                  {/* <Button variant="outline" className="gap-2">
                    <FileText className="w-4 h-4" />
                    Save as RFP
                  </Button> */}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-12 text-center border rounded-lg bg-card">
                <h3 className="text-xl font-medium">No Template Selected</h3>
                <p className="mt-2 text-muted-foreground">
                  Please select a template from the RFP templates page to get
                  started.
                </p>
                <Button
                  className="mt-6 gap-2"
                  onClick={() => router.push("/sourcing/rfp")}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back to Templates
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Resizable Questions Panel */}
      {selectedSubsection && (
        <>
          {/* Resize handle */}
          <div
            className={cn(
              "fixed flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50 ",
              isResizing ? "bg-blue-500/50" : "bg-transparent"
            )}
            style={{
              right: `calc(${width}px + 1px)`,
              top: "-2rem",
              bottom: 0,
              height: "calc(100vh + 2rem)",
            }}
            onMouseDown={handleMouseDown}
          />

          {/* Sidebar panel */}
          <div
            className="fixed right-0 bg-background border-l shadow-lg z-50 pt-10"
            style={{
              width: `${width}px`,
              top: "-2rem",
              bottom: 0,
              height: "calc(100vh + 2rem)",
            }}
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="shrink-0 p-4 border-b bg-background">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">
                      {selectedSubsection}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      These questions help us gather key details, ensuring your
                      RFP responses are accurate and effective.
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setSelectedSection(null);
                      setSelectedSubsection(null);
                      setSelectedSubsectionId(null);
                      setQuestions([]);
                      setSelectedQuestions([]);
                    }}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Questions list */}
              <ScrollArea className="flex-1">
                <div className="p-4 space-y-4">
                  {isLoadingQuestions ? (
                    <div className="space-y-4">
                      {Array(5)
                        .fill(0)
                        .map((_, i) => (
                          <div
                            key={i}
                            className="p-4 border rounded-lg space-y-2"
                          >
                            <div className="flex items-center gap-3">
                              <Skeleton className="h-4 w-4 rounded-sm" />
                              <Skeleton className="h-4 w-full" />
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <>
                      {questions.length > 0 ? (
                        <div className="space-y-4">
                          {questions.map((question) => (
                            <div
                              key={question.question_id}
                              className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                            >
                              <div className="flex items-start gap-3">
                                <Checkbox
                                  checked={selectedQuestions.includes(
                                    question.question_id
                                  )}
                                  onCheckedChange={() =>
                                    handleQuestionSelect(question.question_id)
                                  }
                                />
                                <div className="flex-1">
                                  <p className="text-sm font-medium">
                                    {question.question_name}
                                  </p>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteSingleQuestion(
                                      question.question_id
                                    );
                                  }}
                                  disabled={isProcessing}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-muted-foreground text-center">
                          No questions available for this section
                        </p>
                      )}

                      {/* Show loading indicators for new questions below existing ones */}
                      {isGeneratingFromPrompt && (
                        <div
                          className={cn(
                            "pt-4 mt-4",
                            questions.length > 0 && "border-t"
                          )}
                        >
                          <p className="text-sm text-muted-foreground mb-4">
                            Generating additional questions...
                          </p>
                          <div className="space-y-4">
                            {Array(3)
                              .fill(0)
                              .map((_, i) => (
                                <div
                                  key={i}
                                  className="p-4 border rounded-lg space-y-2"
                                >
                                  <div className="flex items-center gap-3">
                                    <Skeleton className="h-4 w-4 rounded-sm" />
                                    <Skeleton className="h-4 w-full" />
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                  <p className="text-xs mt-2">
                    *Select the questions you want to accept.
                  </p>
                </div>
              </ScrollArea>

              {/* Accept Button */}
              <div className="p-4 border-t bg-background space-y-2">
                <Button
                  className="w-full"
                  onClick={handleAcceptQuestions}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Processing...</span>
                    </div>
                  ) : (
                    `Accept Selected Questions (${selectedQuestions.length})`
                  )}
                </Button>
              </div>

              {/* Chat Input */}
              <div className="p-4 border-t bg-background">
                <SimpleChatInput
                  onSendMessage={handleSendMessage}
                  placeholder="Ask Mipal to generate your own questions by providing the context..."
                  isLoading={isGeneratingFromPrompt}
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Answer Generation Sidebar - now with responsive width */}
      <AnswerGenerationSidebar
        isOpen={isAnswerSidebarOpen}
        onClose={() => {
          setIsAnswerSidebarOpen(false);
          setSelectedQuestion(null);
        }}
        width={
          window.innerWidth < 768
            ? window.innerWidth * 0.95
            : answerSidebarWidth
        }
        isResizing={isAnswerSidebarResizing}
        onMouseDown={handleAnswerSidebarMouseDown}
        selectedSection={selectedSection}
        selectedQuestion={selectedQuestion}
        templateDetails={templateDetails}
        onDocumentUploaded={handleDocumentUploaded}
        refreshTemplate={refetchTemplate}
      />

      {/* Note Sidebar - also with responsive width */}
      {isNoteSidebarOpen && (
        <>
          {/* Resize handle */}
          <div
            className={cn(
              "fixed flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50",
              isNoteSidebarResizing ? "bg-blue-500/50" : "bg-transparent"
            )}
            style={{
              right: `calc(${window.innerWidth < 768 ? window.innerWidth * 0.95 : noteSidebarWidth}px + 1px)`,
              top: "-2rem",
              bottom: 0,
              height: "calc(100vh + 2rem)",
            }}
            onMouseDown={handleNoteSidebarMouseDown}
          />

          {/* Sidebar panel */}
          <div
            className="fixed right-0 bg-background border-l shadow-lg z-50 pt-10"
            style={{
              width: `${window.innerWidth < 768 ? window.innerWidth * 0.95 : noteSidebarWidth}px`,
              top: "-2rem",
              bottom: 0,
              height: "calc(100vh + 2rem)",
            }}
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="shrink-0 p-4 border-b bg-background">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Add Note</h2>
                    <p className="text-sm text-muted-foreground">
                      Add notes for {selectedQuestion?.name}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setIsNoteSidebarOpen(false);
                      setSelectedQuestion(null);
                    }}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Note Input */}
              <div className="flex-1 p-4">
                <Textarea
                  placeholder="Enter your notes here..."
                  className="min-h-[200px] w-full"
                />
              </div>

              {/* Save Button */}
              <div className="p-4 border-t bg-background">
                <Button className="w-full">Save Note</Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
