import React from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  X,
  Loader2,
  BookOpen,
  Upload,
  File,
  Trash2,
  Sparkles,
  Maximize2,
  Minimize2,
  ChevronUp,
  ChevronDown,
  Pencil,
  Check,
  AlertTriangle,
  Zap,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useToggleKnowledgePalMutation,
  useDeleteDocumentMutation,
  useGenerateSectionAnswersMutation,
  useFormDataUploadDocumentMutation,
  useGetTemplateByIdQuery,
  useSaveAnswersMutation,
  useEnhanceQuestionAnswerMutation,
  useGenerateQuestionAnswerMutation,
} from "@/store/services/sourcingApi";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownRenderer } from "@/app/(protected)/chat/components/MarkdownRenderer";
import { toast } from "@/hooks/use-toast";
import MarkdownEditor from "./MarkdownEditor";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FileInfo {
  file_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  created_at: string;
  is_embedded: boolean;
}

// Define a type for Question to ensure consistency
type Question = {
  question_id: string;
  question_name: string;
  is_accepted: boolean;
  answer?: string;
  files?: FileInfo[];
  sources?: Array<any>;
  is_speculative?: boolean | null;
  accepted_answer?: boolean;
};

// Define a type for API response answers
type ApiAnswer = {
  question_id: string;
  question?: string;
  answer: string;
  sources?: any[];
  is_speculative?: boolean;
};

interface AnswerGenerationSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  width: number;
  isResizing: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
  selectedSection: string | null;
  selectedQuestion: {
    id: string;
    name: string;
  } | null;
  templateDetails?: {
    template_id: string;
    sections: Array<{
      heading: string;
      section_id: string;
      knowledge_pal_enabled?: boolean;
      files?: FileInfo[];
      subsections: Array<{
        subheading: string;
        subsection_id?: string;
        questions: Array<Question>;
      }>;
    }>;
  };
  onDocumentUploaded?: () => void;
  refreshTemplate?: () => void;
}

interface UploadedFile {
  file: File;
  id: string;
}

const MAX_TOTAL_SIZE = 2 * 1024 * 1024; // 2MB in bytes

const AnswerGenerationSidebar: React.FC<AnswerGenerationSidebarProps> = ({
  isOpen,
  onClose,
  width,
  isResizing,
  onMouseDown,
  selectedSection,
  selectedQuestion,
  templateDetails,
  onDocumentUploaded,
  refreshTemplate,
}) => {
  const [isProcessing, setIsProcessing] = React.useState(false);
  const [isKnowledgePalEnabled, setIsKnowledgePalEnabled] =
    React.useState(false);
  const [uploadedFiles, setUploadedFiles] = React.useState<UploadedFile[]>([]);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [currentSelectedQuestion, setCurrentSelectedQuestion] = React.useState<{
    id: string;
    name: string;
  } | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [isToggling, setIsToggling] = React.useState(false);
  const [toggleKnowledgePalMutation] = useToggleKnowledgePalMutation();
  const [uploadDocument, { isLoading: isUploading }] =
    useFormDataUploadDocumentMutation();
  const [uploadingFileId, setUploadingFileId] = React.useState<string | null>(
    null
  );

  const [deleteDocument, { isLoading: isDeleting }] =
    useDeleteDocumentMutation();
  const [deletingFileId, setDeletingFileId] = React.useState<string | null>(
    null
  );
  const [isRefetching, setIsRefetching] = React.useState(false);
  const [generateSectionAnswers, { isLoading: isGeneratingAnswers }] =
    useGenerateSectionAnswersMutation();
  const [generateQuestionAnswer, { isLoading: isGeneratingQuestionAnswer }] =
    useGenerateQuestionAnswerMutation();
  const { data: updatedTemplate, refetch: refetchTemplate } =
    useGetTemplateByIdQuery(templateDetails?.template_id || "", {
      skip: !templateDetails?.template_id,
    });
  const [saveAnswers, { isLoading: isSavingAnswers }] =
    useSaveAnswersMutation();
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [isTopSectionCollapsed, setIsTopSectionCollapsed] =
    React.useState(false);
  const [enhanceQuestionAnswer, { isLoading: isEnhancing }] =
    useEnhanceQuestionAnswerMutation();
  const [enhancingQuestionId, setEnhancingQuestionId] = React.useState<
    string | null
  >(null);
  const [isEnhanceDialogOpen, setIsEnhanceDialogOpen] = React.useState(false);
  const [enhancePrompt, setEnhancePrompt] = React.useState<string>("");
  const [selectedQuestionForEnhance, setSelectedQuestionForEnhance] =
    React.useState<string | null>(null);

  // New state for managing editing answers
  const [editingAnswerId, setEditingAnswerId] = React.useState<string | null>(
    null
  );
  const [editedAnswers, setEditedAnswers] = React.useState<
    Record<string, string>
  >({});

  // Add this to the component state at the top
  const [questionSpeculativeStatus, setQuestionSpeculativeStatus] =
    React.useState<Record<string, boolean>>({});

  // Add this to the component state
  const [questionSources, setQuestionSources] = React.useState<
    Record<string, any[]>
  >({});

  // Add state to track which answers have been manually edited
  const [manuallyEditedAnswers, setManuallyEditedAnswers] = React.useState<
    Set<string>
  >(new Set());

  // Add state for enhanced answer preview
  const [enhancedAnswerPreview, setEnhancedAnswerPreview] = React.useState<{
    question_id: string;
    answer: string;
    is_speculative: boolean;
    sources?: any[];
  } | null>(null);
  const [isEnhancedPreviewDialogOpen, setIsEnhancedPreviewDialogOpen] =
    React.useState(false);

  // Get existing files for the current selection (section or question)
  const existingFiles = React.useMemo(() => {
    if (!templateDetails) return [];

    if (currentSelectedQuestion) {
      // Find question files
      const section = templateDetails.sections.find(
        (s) => s.heading === selectedSection
      );
      if (!section) return [];

      for (const subsection of section.subsections) {
        const question = subsection.questions.find(
          (q) => q.question_id === currentSelectedQuestion.id
        );
        if (question && question.files) {
          return question.files;
        }
      }
    } else if (selectedSection) {
      // Find section files
      const section = templateDetails.sections.find(
        (s) => s.heading === selectedSection
      );
      if (section && section.files) {
        return section.files;
      }
    }

    return [];
  }, [templateDetails, selectedSection, currentSelectedQuestion]);

  // Helper to check if the selected question has files in either template
  const hasQuestionFiles = React.useMemo(() => {
    if (!currentSelectedQuestion) return false;

    // First check existing files from templateDetails
    if (existingFiles.length > 0) return true;

    // Then check in the updated template if available
    if (updatedTemplate) {
      const section = updatedTemplate.sections.find(
        (s) => s.heading === selectedSection || s.section_id === selectedSection
      );
      if (!section) return false;

      for (const subsection of section.subsections) {
        const question = subsection.questions.find(
          (q) => q.question_id === currentSelectedQuestion.id
        ) as Question | undefined;
        if (question?.files && question.files.length > 0) {
          return true;
        }
      }
    }

    return false;
  }, [
    currentSelectedQuestion,
    existingFiles,
    updatedTemplate,
    selectedSection,
  ]);

  // Update currentSelectedQuestion when selectedQuestion prop changes
  React.useEffect(() => {
    // When selectedQuestion is null but was previously set, we're switching to section view
    if (!selectedQuestion && currentSelectedQuestion) {
      setCurrentSelectedQuestion(null);
      // Also clear any editing state
      setEditingAnswerId(null);
    }
    // When selectedQuestion is provided, we're switching to question view
    else if (selectedQuestion) {
      setCurrentSelectedQuestion(selectedQuestion);

      // If we're selecting a question, make sure to get its latest answer
      if (updatedTemplate) {
        const latestAnswer = updatedTemplate.sections
          .find((s) => s.heading === selectedSection)
          ?.subsections.flatMap((sub) => sub.questions)
          .find((q) => q.question_id === selectedQuestion.id)?.answer;

        if (latestAnswer) {
          const cleanAnswer = latestAnswer
            .replace(/\\n/g, "\n")
            .replace(/\\"/g, '"');
          // Pre-load the edited answer with the latest answer
          setEditedAnswers((prev) => ({
            ...prev,
            [selectedQuestion.id]: cleanAnswer,
          }));
        }
      }
    }
  }, [
    selectedQuestion,
    updatedTemplate,
    selectedSection,
    currentSelectedQuestion,
  ]);

  // Update isKnowledgePalEnabled state when the section changes
  React.useEffect(() => {
    if (selectedSection && templateDetails) {
      const section = templateDetails.sections.find(
        (s) => s.heading === selectedSection
      );
      if (section) {
        setIsKnowledgePalEnabled(section.knowledge_pal_enabled || false);
      }
    }
  }, [selectedSection, templateDetails]);

  // Modify the useEffect that resets editedAnswers to be more selective
  React.useEffect(() => {
    if (isOpen) {
      // Force a refetch of the template when sidebar is opened
      refetchTemplate();
    }
  }, [isOpen, refetchTemplate]);

  const toggleKnowledgePal = async () => {
    if (!selectedSection || !templateDetails) return;

    // Find the section_id for the selected section
    const section = templateDetails.sections.find(
      (s) => s.heading === selectedSection || s.section_id === selectedSection
    );

    // Use selectedSection directly if it's already a section_id
    const sectionId = section?.section_id || selectedSection;

    const newValue = !isKnowledgePalEnabled;

    try {
      setIsToggling(true);
      await toggleKnowledgePalMutation({
        sectionId: sectionId,
        enabled: newValue,
      }).unwrap();

      // Update local state
      setIsKnowledgePalEnabled(newValue);

      toast({
        title: `Knowledge PAL ${newValue ? "enabled" : "disabled"} successfully`,
        description: `Knowledge PAL ${newValue ? "enabled" : "disabled"} successfully`,
      });
    } catch (error) {
      console.error("Failed to toggle Knowledge PAL:", error);
      toast({
        title: "Failed to toggle Knowledge PAL. Please try again.",
        description: "Failed to toggle Knowledge PAL. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsToggling(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;

    const newFiles = Array.from(e.target.files);
    const currentTotalSize = getTotalSize();
    const newFilesTotalSize = newFiles.reduce(
      (sum, file) => sum + file.size,
      0
    );

    if (currentTotalSize + newFilesTotalSize > MAX_TOTAL_SIZE) {
      setErrorMessage("Total file size cannot exceed 2MB");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setErrorMessage(null);
    setUploadedFiles([
      ...uploadedFiles,
      ...newFiles.map((file) => ({
        file,
        id: Math.random().toString(36).substring(2, 9),
      })),
    ]);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((file) => file.id !== id));
    setErrorMessage(null);
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return "0 bytes";
    if (bytes < 1024) return bytes + " bytes";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const getTotalSize = () => {
    return uploadedFiles.reduce((sum, file) => sum + file.file.size, 0);
  };

  const handleUpdateAnswer = (questionId: string, markdown: string) => {
    setEditedAnswers({
      ...editedAnswers,
      [questionId]: markdown,
    });

    // Track that this answer has been manually edited
    setManuallyEditedAnswers((prev) => {
      const newSet = new Set(prev);
      newSet.add(questionId);
      return newSet;
    });
  };

  const handleSave = async () => {
    // Log all answers for testing purposes
    console.log("Saving answers:", editedAnswers);

    if (!templateDetails?.template_id) return;

    try {
      if (Object.keys(editedAnswers).length > 1) {
        // Multiple answers - use answers array format
        await saveAnswers({
          templateId: templateDetails.template_id,
          answers: Object.entries(editedAnswers).map(
            ([questionId, answer]) => ({
              question_id: questionId,
              answer: answer,
              accept_answer: true,
              is_speculative: manuallyEditedAnswers.has(questionId)
                ? false
                : questionSpeculativeStatus[questionId] || false,
              sources: questionSources[questionId] || [],
            })
          ),
        }).unwrap();

        toast({
          title: "Answers saved",
          description: `Saved ${Object.keys(editedAnswers).length} answers`,
        });
      } else if (Object.keys(editedAnswers).length === 1) {
        // Single answer - use direct format
        const [questionId, answer] = Object.entries(editedAnswers)[0];

        await saveAnswers({
          templateId: templateDetails.template_id,
          question_id: questionId,
          answer: answer,
          accept_answer: true,
          is_speculative: manuallyEditedAnswers.has(questionId)
            ? false
            : questionSpeculativeStatus[questionId] || false,
          sources: questionSources[questionId] || [],
        }).unwrap();

        toast({
          title: "Answer saved",
          description: "Saved answer successfully",
        });
      }

      // Refresh template data and reset edited answers
      await refreshTemplate?.();

      // Clear all state after saving
      setEditedAnswers({});
      setQuestionSpeculativeStatus({});
      setQuestionSources({});
      setManuallyEditedAnswers(new Set());

      // Close sidebar after successful save
      onClose();
    } catch (error) {
      console.error("Failed to save answers:", error);
      toast({
        title: "Failed to save answers",
        description:
          "There was an error saving your answers. Please try again.",
        variant: "destructive",
      });
    }
  };

  const uploadFile = async (fileId: string) => {
    if (!templateDetails) {
      toast({
        title: "No template ",
        description: "No template or section selected",
        variant: "destructive",
      });
      return;
    }
    if (!selectedSection) {
      toast({
        title: "No  section selected",
        description: "No template or section selected",
        variant: "destructive",
      });
      return;
    }

    // Find the section by heading or section_id
    const section = templateDetails.sections.find(
      (s) => s.heading === selectedSection || s.section_id === selectedSection
    );

    // Use selectedSection directly if it's already a section_id
    const sectionId = section?.section_id || selectedSection;

    const fileToUpload = uploadedFiles.find((f) => f.id === fileId);
    if (!fileToUpload) {
      toast({
        title: "File not found",
        description: "File not found",
        variant: "destructive",
      });
      return;
    }

    try {
      setUploadingFileId(fileId);

      const data = await uploadDocument({
        templateId: templateDetails.template_id,
        sectionId: sectionId,
        questionId: currentSelectedQuestion?.id || null,
        file: fileToUpload.file,
      }).unwrap();
      console.log("data", data);

      // Remove from local state after successful upload
      setUploadedFiles((prev) => prev.filter((file) => file.id !== fileId));
      onDocumentUploaded?.();
      setIsRefetching(true);

      // Wait a bit for the template to refresh
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        title: `${fileToUpload.file.name} uploaded successfully`,
        description: `${fileToUpload.file.name} uploaded successfully`,
      });
    } catch (error) {
      console.error("Failed to upload file:", error);
      toast({
        title: `Failed to upload ${fileToUpload.file.name}`,
        description: `Failed to upload ${fileToUpload.file.name}`,
        variant: "destructive",
      });
    } finally {
      setUploadingFileId(null);
      setIsRefetching(false);
    }
  };

  const uploadAllFiles = async () => {
    if (uploadedFiles.length === 0) return;

    const promises = uploadedFiles.map((file) => uploadFile(file.id));
    await Promise.all(promises);
  };

  // Add delete file handler
  const handleDeleteFile = async (fileId: string) => {
    if (!templateDetails) return;

    try {
      setDeletingFileId(fileId);
      await deleteDocument({ fileId }).unwrap();
      await refreshTemplate?.();
      toast({
        title: "File deleted successfully",
        description: "File deleted successfully",
      });
    } catch (error) {
      console.error("Failed to delete file:", error);
      toast({
        title: "Failed to delete file",
        description: "Failed to delete file",
        variant: "destructive",
      });
    } finally {
      setDeletingFileId(null);
    }
  };

  const handleGenerateAnswers = async () => {
    if (!templateDetails || !selectedSection) return;

    const section = templateDetails.sections.find(
      (s) => s.heading === selectedSection || s.section_id === selectedSection
    );

    // Use selectedSection directly if it's already a section_id
    const sectionId = section?.section_id || selectedSection;

    try {
      console.log("Calling generateSectionAnswers with:", {
        sectionId,
        templateId: templateDetails.template_id,
      });

      const result = await generateSectionAnswers({
        sectionId: sectionId,
        templateId: templateDetails.template_id,
      }).unwrap();

      console.log("Generated answers:", result);

      // Process the answers from the API response
      if (Array.isArray(result) && result.length > 0) {
        const newAnswers: Record<string, string> = {};
        const speculativeFlags: Record<string, boolean> = {};
        const sourceData: Record<string, any[]> = {};

        (result as ApiAnswer[]).forEach((item) => {
          if (item.question_id && item.answer) {
            newAnswers[item.question_id] = item.answer;

            // Store the speculative flag if present
            if (typeof item.is_speculative === "boolean") {
              speculativeFlags[item.question_id] = item.is_speculative;
            }

            // Store sources if present
            if (item.sources && Array.isArray(item.sources)) {
              sourceData[item.question_id] = item.sources;
            }
          }
        });

        // Set the answers in state to display them immediately
        setEditedAnswers(newAnswers);

        // Store speculative status in state for immediate UI updates
        setQuestionSpeculativeStatus(speculativeFlags);

        // Store sources in state
        setQuestionSources(sourceData);

        // Update the template to include speculative flags
        if (updatedTemplate) {
          // Create a deep copy of the sections to avoid modifying read-only objects
          const updatedSections = JSON.parse(
            JSON.stringify(updatedTemplate.sections)
          );
          const sectionIndex = updatedSections.findIndex(
            (s: any) =>
              s.heading === selectedSection || s.section_id === selectedSection
          );

          if (sectionIndex !== -1) {
            updatedSections[sectionIndex].subsections.forEach(
              (subsection: any) => {
                subsection.questions.forEach((question: any) => {
                  if (speculativeFlags[question.question_id] !== undefined) {
                    question.is_speculative =
                      speculativeFlags[question.question_id];
                  }

                  // Also update sources if available
                  if (sourceData[question.question_id]) {
                    question.sources = sourceData[question.question_id];
                  }
                });
              }
            );
          }
        }

        // Count speculative vs. sourced answers
        const speculativeCount =
          Object.values(speculativeFlags).filter(Boolean).length;
        const sourcedCount = result.length - speculativeCount;

        toast({
          title: "Answers generated successfully",
          description:
            speculativeCount > 0
              ? `Generated ${sourcedCount} sourced and ${speculativeCount} AI-generated answers`
              : `Generated ${result.length} answers from your documents`,
        });
      } else if (Array.isArray(result) && result.length === 0) {
        // Handle empty result array
        toast({
          title: "No answers generated",
          description: "No questions found to generate answers for.",
        });
      } else {
        // Fallback to refetching if result is not in expected format
        await refetchTemplate();
        setEditedAnswers({});

        toast({
          title: "Answers generated successfully",
          description: "Template updated with new answers.",
        });
      }

      // Double check with another refresh after a short delay to ensure we get the updated data
      setTimeout(async () => {
        await refetchTemplate();
      }, 1000);
    } catch (error: any) {
      console.error("Failed to generate answers:", error);

      // Check if the error is actually a valid response with speculative answers
      // This could happen if RTK Query is incorrectly handling the response
      if (error.data && Array.isArray(error.data) && error.data.length > 0) {
        console.log("Found valid answer data in error object:", error.data);

        try {
          // Process answers from the error.data
          const result = error.data;
          const newAnswers: Record<string, string> = {};
          const speculativeFlags: Record<string, boolean> = {};
          const sourceData: Record<string, any[]> = {};

          result.forEach((item: ApiAnswer) => {
            if (item.question_id && item.answer) {
              newAnswers[item.question_id] = item.answer;

              // Store the speculative flag if present
              if (typeof item.is_speculative === "boolean") {
                speculativeFlags[item.question_id] = item.is_speculative;
              }

              // Store sources if present
              if (item.sources && Array.isArray(item.sources)) {
                sourceData[item.question_id] = item.sources;
              }
            }
          });

          // Set the answers in state
          setEditedAnswers(newAnswers);
          setQuestionSpeculativeStatus(speculativeFlags);
          setQuestionSources(sourceData);

          // Count speculative vs. sourced answers
          const speculativeCount =
            Object.values(speculativeFlags).filter(Boolean).length;
          const sourcedCount = result.length - speculativeCount;

          toast({
            title: "Answers generated successfully",
            description:
              speculativeCount > 0
                ? `Generated ${sourcedCount} sourced and ${speculativeCount} AI-generated answers`
                : `Generated ${result.length} answers from your documents`,
          });

          // Refresh template
          await refetchTemplate();
          return;
        } catch (processingError) {
          console.error(
            "Error processing answer data from error object:",
            processingError
          );
        }
      }

      // If we reach here, it's a genuine error
      const errorMessage =
        error.data?.details || error.message || "Unknown error occurred";
      toast({
        title: "Failed to generate answers",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  // Reset hasGeneratedAnswers when section changes
  React.useEffect(() => {
    setIsRefetching(false);
  }, [selectedSection]);

  const getQuestionAnswer = (questionId: string) => {
    // First check for local edited answers
    if (editedAnswers[questionId]) {
      console.log(`Using edited answer for question ${questionId}`);
      return editedAnswers[questionId];
    }

    // Look in the most up-to-date template data
    const answer = updatedTemplate?.sections
      .find(
        (s) => s.heading === selectedSection || s.section_id === selectedSection
      )
      ?.subsections.flatMap((sub) => sub.questions)
      .find((q) => q.question_id === questionId)?.answer;

    // If not found in updated template, check in original template
    if (!answer && templateDetails) {
      const fallbackAnswer = templateDetails.sections
        .find(
          (s) =>
            s.heading === selectedSection || s.section_id === selectedSection
        )
        ?.subsections.flatMap((sub) => sub.questions)
        .find((q) => q.question_id === questionId)?.answer;

      if (fallbackAnswer) {
        console.log(`Using fallback answer for question ${questionId}`);
        return fallbackAnswer.replace(/\\n/g, "\n").replace(/\\"/g, '"');
      }
    }

    // Clean up the markdown content by removing any escaped characters
    return answer ? answer.replace(/\\n/g, "\n").replace(/\\"/g, '"') : "";
  };

  const handleStartEditing = (questionId: string) => {
    setEditingAnswerId(questionId);

    // If we don't already have an edited version, initialize with the current answer
    if (!editedAnswers[questionId]) {
      setEditedAnswers({
        ...editedAnswers,
        [questionId]: getQuestionAnswer(questionId),
      });
    }
  };

  const handleSaveEdit = (questionId: string) => {
    setEditingAnswerId(null);

    // We need to ensure the edited answer is visible after closing the editor
    // by explicitly loading it from editedAnswers into the state
    if (editedAnswers[questionId]) {
      // Get the latest edited version for this question
      const updatedAnswer = editedAnswers[questionId];

      // Make sure it's immediately visible in the UI by updating state
      setEditedAnswers({
        ...editedAnswers,
        [questionId]: updatedAnswer,
      });
    }
  };

  // Function to handle enhancing an answer
  const handleOpenEnhanceDialog = (questionId: string) => {
    setSelectedQuestionForEnhance(questionId);
    setIsEnhanceDialogOpen(true);
  };

  const handleEnhanceAnswer = async () => {
    if (!templateDetails?.template_id || !selectedQuestionForEnhance) return;

    try {
      setEnhancingQuestionId(selectedQuestionForEnhance);
      setIsEnhanceDialogOpen(false);

      // Call the enhance API
      const result = await enhanceQuestionAnswer({
        questionId: selectedQuestionForEnhance,
        prompt: enhancePrompt,
      }).unwrap();

      console.log("Enhanced answer result:", result);

      // Instead of immediately updating the template, show the preview dialog
      if (result) {
        setEnhancedAnswerPreview({
          question_id: selectedQuestionForEnhance,
          answer: result.answer || "",
          is_speculative: result.is_speculative || false,
          sources: result.sources || [],
        });
        setIsEnhancedPreviewDialogOpen(true);
      } else {
        toast({
          title: "Error enhancing answer",
          description: "No valid response received from the server.",
          variant: "destructive",
        });
      }

      setEnhancePrompt("");
    } catch (error) {
      console.error("Failed to enhance answer:", error);
      toast({
        title: "Failed to enhance answer",
        description:
          "There was an error enhancing the answer. Please try again.",
        variant: "destructive",
      });
      setEnhancingQuestionId(null);
      setSelectedQuestionForEnhance(null);
    }
  };

  // Function to apply the enhanced answer
  const applyEnhancedAnswer = () => {
    if (!enhancedAnswerPreview) return;

    // Update the edited answers with the enhanced answer
    setEditedAnswers({
      ...editedAnswers,
      [enhancedAnswerPreview.question_id]: enhancedAnswerPreview.answer,
    });

    // Update speculative status
    setQuestionSpeculativeStatus({
      ...questionSpeculativeStatus,
      [enhancedAnswerPreview.question_id]: enhancedAnswerPreview.is_speculative,
    });

    // Update sources if available
    if (enhancedAnswerPreview.sources) {
      setQuestionSources({
        ...questionSources,
        [enhancedAnswerPreview.question_id]: enhancedAnswerPreview.sources,
      });
    }

    // Close the preview dialog
    setIsEnhancedPreviewDialogOpen(false);
    setEnhancedAnswerPreview(null);
    setEnhancingQuestionId(null);

    toast({
      title: "Answer enhanced",
      description: "The enhanced answer has been applied.",
    });
  };

  // Function to dismiss the enhanced answer
  const dismissEnhancedAnswer = () => {
    setIsEnhancedPreviewDialogOpen(false);
    setEnhancedAnswerPreview(null);
    setEnhancingQuestionId(null);
  };

  // Custom renderer for question answers that supports editing
  const renderQuestionAnswer = (
    question: Pick<
      Question,
      "question_id" | "question_name" | "is_speculative"
    >,
    questionIndex: number
  ) => {
    const isEditing = editingAnswerId === question.question_id;
    const answerContent = getQuestionAnswer(question.question_id);

    // Check for speculative status from multiple sources with priority
    const isSpeculative =
      questionSpeculativeStatus[question.question_id] !== undefined
        ? questionSpeculativeStatus[question.question_id]
        : question.is_speculative !== undefined
          ? question.is_speculative
          : (
              updatedTemplate?.sections
                .find(
                  (s) =>
                    s.heading === selectedSection ||
                    s.section_id === selectedSection
                )
                ?.subsections.flatMap((sub) => sub.questions)
                .find((q) => q.question_id === question.question_id) as
                | Question
                | undefined
            )?.is_speculative;

    // Get sources from state or template
    const sources =
      questionSources[question.question_id] ||
      (
        updatedTemplate?.sections
          .find(
            (s) =>
              s.heading === selectedSection || s.section_id === selectedSection
          )
          ?.subsections.flatMap((sub) => sub.questions)
          .find((q) => q.question_id === question.question_id) as
          | Question
          | undefined
      )?.sources ||
      [];

    return (
      <div className="p-4 rounded-lg border bg-muted/30 mb-10">
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center min-w-6 h-6 w-6 rounded-full bg-primary/10 text-primary text-xs font-medium">
                Q{questionIndex + 1}
              </div>
              <p className="text-[16px] font-medium">
                {question.question_name}
              </p>
            </div>

            <div className="flex items-center gap-1">
              {/* Enhance Button */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() =>
                        handleOpenEnhanceDialog(question.question_id)
                      }
                      disabled={
                        isEnhancing &&
                        enhancingQuestionId === question.question_id
                      }
                      title="Enhance this answer"
                    >
                      {isEnhancing &&
                      enhancingQuestionId === question.question_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Zap className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Enhance this answer</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              {/* Edit Button */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() =>
                        isEditing
                          ? handleSaveEdit(question.question_id)
                          : handleStartEditing(question.question_id)
                      }
                    >
                      {isEditing ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Pencil className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Edit this answer</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>

          {/* Speculative Answer Warning */}
          {isSpeculative && (
            <div className="flex items-center gap-2 p-2 mb-3 bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200 rounded-md text-sm">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>
                This is a speculative answer generated without source documents.
              </span>
            </div>
          )}

          {/* if template is generating answer and if template api is loading */}
          {isGeneratingAnswers || isRefetching ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : isEditing ? (
            <div className="markdown-editor-wrapper">
              <style jsx global>{`
                .ProseMirror table {
                  border-collapse: collapse;
                  margin: 0;
                  overflow: hidden;
                  table-layout: fixed;
                  width: 100%;
                }

                .ProseMirror table td,
                .ProseMirror table th {
                  border: 2px solid #ced4da;
                  box-sizing: border-box;
                  min-width: 1em;
                  padding: 8px;
                  position: relative;
                  vertical-align: top;
                }

                .ProseMirror table th {
                  background-color: #f8f9fa;
                  font-weight: bold;
                  text-align: left;
                }

                .ProseMirror table .selectedCell:after {
                  background: rgba(200, 200, 255, 0.4);
                  content: "";
                  left: 0;
                  right: 0;
                  top: 0;
                  bottom: 0;
                  pointer-events: none;
                  position: absolute;
                  z-index: 2;
                }

                .ProseMirror table .column-resize-handle {
                  background-color: #adf;
                  bottom: -2px;
                  position: absolute;
                  right: -2px;
                  pointer-events: none;
                  top: 0;
                  width: 4px;
                }

                .ProseMirror table p {
                  margin: 0;
                }
              `}</style>
              <MarkdownEditor
                content={answerContent}
                onChange={(markdown) =>
                  handleUpdateAnswer(question.question_id, markdown)
                }
              />
            </div>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={answerContent} />
            </div>
          )}
        </div>
      </div>
    );
  };

  // Make preloadAnswersFromTemplate more efficient
  const preloadAnswersFromTemplate = React.useCallback(() => {
    if (!updatedTemplate || !selectedSection) return;

    const currentSection = updatedTemplate.sections.find(
      (s) => s.heading === selectedSection
    );
    if (!currentSection) return;

    // Get all questions with answers for the current section
    const questionsWithAnswers = currentSection.subsections
      .flatMap((sub) => sub.questions)
      .filter((q) => q.answer && q.answer.trim() !== "");

    // Pre-load new answers only
    const newEditedAnswers = { ...editedAnswers };
    const newSpeculativeStatus = { ...questionSpeculativeStatus };
    let hasChanges = false;

    // Only add answers that aren't already in editedAnswers
    questionsWithAnswers.forEach((question) => {
      if (question.answer && !editedAnswers[question.question_id]) {
        // Add the answer
        newEditedAnswers[question.question_id] = question.answer
          .replace(/\\n/g, "\n")
          .replace(/\\"/g, '"');

        // Check if question has is_speculative property
        if (
          "is_speculative" in question &&
          typeof question.is_speculative === "boolean"
        ) {
          newSpeculativeStatus[question.question_id] = question.is_speculative;
        }

        hasChanges = true;
      }
    });

    if (hasChanges) {
      setEditedAnswers(newEditedAnswers);
      setQuestionSpeculativeStatus(newSpeculativeStatus);
    }
  }, [
    updatedTemplate,
    selectedSection,
    editedAnswers,
    questionSpeculativeStatus,
  ]);

  // Call preload when template data updates
  React.useEffect(() => {
    if (updatedTemplate) {
      preloadAnswersFromTemplate();
    }
  }, [updatedTemplate, preloadAnswersFromTemplate]);

  // Split into two effects for better separation of concerns
  // Effect 1: Handle sidebar open/close
  React.useEffect(() => {
    if (isOpen) {
      // Force a refetch of the template when sidebar is opened
      refetchTemplate();
    } else {
      // Clear all state when the sidebar is closed
      setEditedAnswers({});
      setEditingAnswerId(null);
      setQuestionSpeculativeStatus({});
      setQuestionSources({});
    }
  }, [isOpen, refetchTemplate]);

  // Effect 2: Handle section/question changes
  React.useEffect(() => {
    if (isOpen && (selectedSection || selectedQuestion)) {
      // When section or question changes, refetch the template
      refetchTemplate();
    }
  }, [isOpen, selectedSection, selectedQuestion, refetchTemplate]);

  // Add new function to handle generating an answer for a specific question
  const handleGenerateQuestionAnswer = async () => {
    if (!templateDetails || !selectedSection || !currentSelectedQuestion) {
      console.error("Missing required data:", {
        templateDetails: !!templateDetails,
        selectedSection,
        currentSelectedQuestion,
      });
      return;
    }

    // Find the section by heading or section_id
    const section = templateDetails.sections.find(
      (s) => s.heading === selectedSection || s.section_id === selectedSection
    );

    // Use selectedSection directly if it's already a section_id
    const sectionId = section?.section_id || selectedSection;

    console.log("Section found:", {
      selectedSection,
      foundSection: !!section,
      sectionId,
    });

    try {
      setIsProcessing(true);

      console.log("Generating answer for question:", {
        questionId: currentSelectedQuestion.id,
        sectionId: sectionId,
        templateId: templateDetails.template_id,
      });

      // Call the new API endpoint to generate an answer for the specific question
      const result = await generateQuestionAnswer({
        questionId: currentSelectedQuestion.id,
        sectionId: sectionId,
        templateId: templateDetails.template_id,
      }).unwrap();

      console.log("Generate question answer result:", result);

      // Process the answer from the API response
      if (result && (Array.isArray(result) || typeof result === "object")) {
        const newAnswer = Array.isArray(result)
          ? result[0]
          : (result as ApiAnswer);

        if (newAnswer && newAnswer.question_id && newAnswer.answer) {
          // Set the answer in state to display it immediately
          setEditedAnswers({
            [newAnswer.question_id]: newAnswer.answer,
          });

          // Store speculative status in state for immediate UI updates
          if (typeof newAnswer.is_speculative === "boolean") {
            setQuestionSpeculativeStatus({
              ...questionSpeculativeStatus,
              [newAnswer.question_id]: newAnswer.is_speculative,
            });
          }

          // Store sources in state if present
          if (newAnswer.sources && Array.isArray(newAnswer.sources)) {
            setQuestionSources({
              ...questionSources,
              [newAnswer.question_id]: newAnswer.sources,
            });
          }

          // Update the template if available
          if (updatedTemplate) {
            // Create a deep copy of the sections to avoid modifying read-only objects
            const updatedSections = JSON.parse(
              JSON.stringify(updatedTemplate.sections)
            );
            const sectionIndex = updatedSections.findIndex(
              (s: any) =>
                s.heading === selectedSection ||
                s.section_id === selectedSection
            );

            if (sectionIndex !== -1) {
              for (const subsection of updatedSections[sectionIndex]
                .subsections) {
                const questionIndex = subsection.questions.findIndex(
                  (q: any) => q.question_id === newAnswer.question_id
                );
                if (questionIndex !== -1) {
                  // Update speculative flag
                  if (typeof newAnswer.is_speculative === "boolean") {
                    subsection.questions[questionIndex].is_speculative =
                      newAnswer.is_speculative;
                  }

                  // Update sources
                  if (newAnswer.sources && Array.isArray(newAnswer.sources)) {
                    subsection.questions[questionIndex].sources =
                      newAnswer.sources;
                  }

                  break;
                }
              }
            }
          }

          // Show appropriate toast
          const isAnswerSpeculative =
            typeof newAnswer.is_speculative === "boolean"
              ? newAnswer.is_speculative
              : false;
          toast({
            title: "Answer generated successfully",
            description: isAnswerSpeculative
              ? "The answer has been generated based on AI knowledge."
              : "The answer has been generated based on the attached documents.",
          });
        } else {
          // Fallback to refetching if result is not in expected format
          const refreshResult = await refetchTemplate();
          console.log("Refetch result:", refreshResult);

          // Clear any edited answers for this question to show the newly generated answer
          const newEditedAnswers = { ...editedAnswers };
          delete newEditedAnswers[currentSelectedQuestion.id];
          setEditedAnswers(newEditedAnswers);

          toast({
            title: "Answer generated successfully",
            description: "The answer has been generated successfully.",
          });
        }
      } else {
        // Fallback to refetching if result is not in expected format
        console.log("Refetching template after generating answer");
        const refreshResult = await refetchTemplate();
        console.log("Refetch result:", refreshResult);

        toast({
          title: "Answer generated successfully",
          description: "The answer has been generated successfully.",
        });
      }
    } catch (error: any) {
      console.error("Failed to generate answer:", error);

      // Check if the error is actually a valid response with a speculative answer
      // This could happen if RTK Query is incorrectly handling the response
      if (
        error.data &&
        (Array.isArray(error.data) || typeof error.data === "object")
      ) {
        console.log("Found valid answer data in error object:", error.data);

        try {
          // Process answer from the error.data
          const newAnswer = Array.isArray(error.data)
            ? error.data[0]
            : error.data;

          if (newAnswer && newAnswer.question_id && newAnswer.answer) {
            // Set the answer in state
            setEditedAnswers({
              [newAnswer.question_id]: newAnswer.answer,
            });

            // Store speculative status
            if (typeof newAnswer.is_speculative === "boolean") {
              setQuestionSpeculativeStatus({
                ...questionSpeculativeStatus,
                [newAnswer.question_id]: newAnswer.is_speculative,
              });
            }

            // Store sources
            if (newAnswer.sources && Array.isArray(newAnswer.sources)) {
              setQuestionSources({
                ...questionSources,
                [newAnswer.question_id]: newAnswer.sources,
              });
            }

            // Show appropriate toast
            const isAnswerSpeculative =
              typeof newAnswer.is_speculative === "boolean"
                ? newAnswer.is_speculative
                : false;
            toast({
              title: "Answer generated successfully",
              description: isAnswerSpeculative
                ? "The answer has been generated based on AI knowledge."
                : "The answer has been generated based on the attached documents.",
            });

            // Refresh template
            await refetchTemplate();
            return;
          }
        } catch (processingError) {
          console.error(
            "Error processing answer data from error object:",
            processingError
          );
        }
      }

      // Show more specific error message for genuine errors
      const errorMessage =
        error.data?.details || error.message || "Unknown error occurred";
      toast({
        title: "Failed to generate answer",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Add a custom close handler to clear state
  const handleClose = () => {
    // Clear all state when manually closing
    setEditedAnswers({});
    setEditingAnswerId(null);
    setQuestionSpeculativeStatus({});
    setQuestionSources({});

    // Call the original onClose
    onClose();
  };

  if (!isOpen) return null;

  if (!templateDetails) {
    return (
      <div
        className="fixed right-0 bg-background border-l shadow-lg z-50 pt-10"
        style={{ width: `${width}px` }}
      >
        <div className="flex flex-col h-full">
          <div className="shrink-0 p-4 border-b">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
          <div className="flex-1 p-4">
            <Skeleton className="h-8 w-full mb-4" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Resize handle */}
      <div
        className={cn(
          "fixed flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50",
          isResizing ? "bg-blue-500/50" : "bg-transparent",
          isExpanded && "hidden"
        )}
        style={{
          right: `calc(${width}px + 1px)`,
          top: "-2rem",
          bottom: 0,
          height: "calc(100vh + 2rem)",
        }}
        onMouseDown={onMouseDown}
      />

      {/* Enhance Dialog */}
      <Dialog
        open={isEnhanceDialogOpen}
        onOpenChange={(open) => {
          setIsEnhanceDialogOpen(open);
          setEnhancePrompt("");
        }}
      >
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Enhance Answer</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="enhance-prompt">Enhancement Prompt</Label>
              <Textarea
                id="enhance-prompt"
                placeholder="Enter instructions on how to enhance the answer..."
                value={enhancePrompt}
                onChange={(e) => setEnhancePrompt(e.target.value)}
                className="min-h-[100px]"
              />
              <p className="text-xs text-muted-foreground">
                Provide specific instructions on how you'd like the answer to be
                enhanced. For example: "Add more technical details" or "Include
                cost analysis".
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsEnhanceDialogOpen(false);
                setEnhancePrompt("");
              }}
            >
              Cancel
            </Button>
            {/* disable enhance button if enhance prompt is empty */}
            <Button
              onClick={handleEnhanceAnswer}
              disabled={isEnhancing || enhancePrompt.trim() === ""}
            >
              {isEnhancing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enhancing...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Enhance
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Enhanced Answer Preview Dialog */}
      <Dialog
        open={isEnhancedPreviewDialogOpen}
        onOpenChange={(open) => {
          if (!open) dismissEnhancedAnswer();
        }}
      >
        <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Enhanced Answer Preview</DialogTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Review the enhanced answer before applying it to your document.
            </p>
          </DialogHeader>

          <div className="flex-1 overflow-auto my-4 border rounded-md p-4 bg-muted/20">
            {enhancedAnswerPreview && (
              <>
                {/* Speculative badge if applicable */}
                {enhancedAnswerPreview.is_speculative && (
                  <div className="flex items-center gap-2 p-2 mb-3 bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200 rounded-md text-sm">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                    <span>
                      This is a speculative answer generated without source
                      documents.
                    </span>
                  </div>
                )}

                {/* Answer content */}
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <MarkdownRenderer content={enhancedAnswerPreview.answer} />
                </div>

                {/* Sources if available */}
                {enhancedAnswerPreview.sources &&
                  enhancedAnswerPreview.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <h4 className="text-sm font-medium mb-2">Sources</h4>
                      <ul className="text-xs text-muted-foreground space-y-1">
                        {enhancedAnswerPreview.sources.map((source, index) => (
                          <li key={index} className="flex items-center gap-2">
                            <FileText className="h-3 w-3 flex-shrink-0" />
                            <span>{source.file_name}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={dismissEnhancedAnswer}>
              Discard
            </Button>
            <Button onClick={applyEnhancedAnswer}>Apply Enhanced Answer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Sidebar panel */}
      <div
        className={cn(
          "fixed right-0 bg-background border-l shadow-lg z-50 pt-10",
          isExpanded ? "w-full" : ""
        )}
        style={{
          width: isExpanded ? "100%" : `${width}px`,
          top: "-2rem",
          bottom: 0,
          height: "calc(100vh + 2rem)",
        }}
      >
        <div
          className={cn(
            "flex flex-col h-full",
            isExpanded && "max-w-[1400px] mx-auto md:px-8"
          )}
        >
          {/* Header */}
          <div className="shrink-0 p-4 border-b bg-background">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">
                  {currentSelectedQuestion ? "Edit Answer" : "Generate Answers"}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                {/* <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    // Reset edited answers and refetch template data
                    setEditedAnswers({});
                    const result = await refetchTemplate();
                    
                    // Force reset of edited answers again after data is loaded
                    if (result.data) {
                      setEditedAnswers({});
                      setEditingAnswerId(null);
                    }
                    
                    toast({
                      title: "Answers refreshed",
                      description: "Cleared edits and loaded latest answers"
                    });
                  }}
                  className="h-8"
                  title="Clear edits and refresh answer data"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Reset & Refresh
                </Button> */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    setIsTopSectionCollapsed(!isTopSectionCollapsed)
                  }
                  className="h-8 w-8"
                >
                  {isTopSectionCollapsed ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronUp className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="h-8 w-8"
                >
                  {isExpanded ? (
                    <Minimize2 className="h-4 w-4" />
                  ) : (
                    <Maximize2 className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleClose}
                  disabled={isProcessing || isToggling}
                  className="h-8 w-8"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Collapsible Top Section */}
          <div
            className={cn(
              "transition-all duration-300 ease-in-out overflow-hidden",
              isTopSectionCollapsed ? "max-h-0" : "max-h-[500px]"
            )}
          >
            {/* Knowledge Pal Toggle */}
            <div className="p-4 border-b bg-background/80">
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-medium pr-4">
                    Enable Knowledge PAL to generate answers with company
                    knowledge
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    className={cn(
                      "rounded-full",
                      isKnowledgePalEnabled
                        ? "border-primary/60 bg-primary/10"
                        : ""
                    )}
                    onClick={toggleKnowledgePal}
                    disabled={isToggling}
                  >
                    {isToggling ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <BookOpen className="mr-2 h-4 w-4 text-green-500" />
                    )}
                    Knowledge PAL
                  </Button>
                </div>

                <div className="space-y-4">
                  {/* Knowledge PAL Status */}
                  {/* <div className={cn(
                    "p-3 rounded-lg border transition-colors",
                    isKnowledgePalEnabled 
                      ? "border-green-500/20 bg-green-500/5" 
                      : "border-muted"
                  )}> */}
                  {/* <div className="flex items-start gap-3">
                      <div className={cn(
                        "h-8 w-8 rounded-full flex items-center justify-center",
                        isKnowledgePalEnabled 
                          ? "bg-green-500/10 text-green-500" 
                          : "bg-muted text-muted-foreground"
                      )}>
                        <BookOpen className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">
                          {isKnowledgePalEnabled 
                            ? "Knowledge PAL is enabled" 
                            : "Knowledge PAL is disabled"}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {isKnowledgePalEnabled 
                            ? "Using company knowledge base to generate better answers"
                            : "Enable to use company knowledge base for better answers"}
                        </p>
                      </div>
                    </div> */}
                  {/* </div> */}

                  {/* File Upload Section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium">Upload Documents</h4>
                      {(uploadedFiles.length > 0 ||
                        existingFiles.length > 0) && (
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(
                            getTotalSize() +
                              existingFiles.reduce(
                                (sum, file) => sum + file.file_size,
                                0
                              )
                          )}{" "}
                          total
                        </p>
                      )}
                    </div>

                    <div
                      className={cn(
                        "border-2 border-dashed rounded-lg p-4 transition-colors",
                        uploadedFiles.length > 0 || existingFiles.length > 0
                          ? "border-primary/20"
                          : "border-muted"
                      )}
                    >
                      <input
                        type="file"
                        id="file-upload"
                        ref={fileInputRef}
                        accept=".pdf,.docx,.doc"
                        className="hidden"
                        onChange={handleFileChange}
                        multiple
                      />
                      <label
                        htmlFor="file-upload"
                        className="cursor-pointer flex flex-col items-center justify-center"
                      >
                        <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                        <p className="text-sm font-medium">
                          Click to upload or drag and drop
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          PDF, DOCX (Max 2MB total)
                        </p>
                      </label>
                    </div>

                    {/* Error message */}
                    {errorMessage && (
                      <div className="rounded-md bg-destructive/10 p-3 text-destructive text-sm">
                        {errorMessage}
                      </div>
                    )}

                    {/* Combined File List (both existing and pending upload) */}
                    <div className="space-y-2">
                      <h5 className="text-xs font-medium text-muted-foreground">
                        Files
                      </h5>

                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {!templateDetails ? (
                          <>
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                          </>
                        ) : (
                          <>
                            {/* Existing Files */}
                            {existingFiles.map((file) => (
                              <div
                                key={file.file_id}
                                className="flex items-center justify-between p-2 rounded-md border bg-muted/50"
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                  <span className="text-sm truncate">
                                    {file.file_name}
                                  </span>
                                  <span className="text-xs text-muted-foreground flex-shrink-0">
                                    {formatFileSize(file.file_size)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-6 w-6 flex-shrink-0 hover:bg-destructive/10 hover:text-destructive"
                                    onClick={() =>
                                      handleDeleteFile(file.file_id)
                                    }
                                    disabled={
                                      isDeleting &&
                                      deletingFileId === file.file_id
                                    }
                                  >
                                    {isDeleting &&
                                    deletingFileId === file.file_id ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      <Trash2 className="h-3 w-3" />
                                    )}
                                  </Button>
                                </div>
                              </div>
                            ))}

                            {/* Question-specific files when a question is selected */}
                            {currentSelectedQuestion &&
                              (() => {
                                const question = updatedTemplate?.sections
                                  .find(
                                    (s) =>
                                      s.heading === selectedSection ||
                                      s.section_id === selectedSection
                                  )
                                  ?.subsections.flatMap((sub) => sub.questions)
                                  .find(
                                    (q) =>
                                      q.question_id ===
                                      currentSelectedQuestion.id
                                  ) as Question | undefined;

                                if (
                                  question?.files &&
                                  question.files.length > 0
                                ) {
                                  return (
                                    <>
                                      <div className="text-xs font-medium text-muted-foreground mt-3 mb-2">
                                        Question Files
                                      </div>
                                      {question.files.map((file) => (
                                        <div
                                          key={file.file_id}
                                          className="flex items-center justify-between p-2 rounded-md border bg-muted/50"
                                        >
                                          <div className="flex items-center gap-2 flex-1 min-w-0">
                                            <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                            <span className="text-sm truncate">
                                              {file.file_name}
                                            </span>
                                            <span className="text-xs text-muted-foreground flex-shrink-0">
                                              {formatFileSize(file.file_size)}
                                            </span>
                                          </div>
                                          <div className="flex items-center gap-1">
                                            <Button
                                              size="icon"
                                              variant="ghost"
                                              className="h-6 w-6 flex-shrink-0 hover:bg-destructive/10 hover:text-destructive"
                                              onClick={() =>
                                                handleDeleteFile(file.file_id)
                                              }
                                              disabled={
                                                isDeleting &&
                                                deletingFileId === file.file_id
                                              }
                                            >
                                              {isDeleting &&
                                              deletingFileId ===
                                                file.file_id ? (
                                                <Loader2 className="h-3 w-3 animate-spin" />
                                              ) : (
                                                <Trash2 className="h-3 w-3" />
                                              )}
                                            </Button>
                                          </div>
                                        </div>
                                      ))}
                                    </>
                                  );
                                }
                                return null;
                              })()}

                            {/* Pending Upload Files */}
                            {uploadedFiles.map((file) => (
                              <div
                                key={file.id}
                                className="flex items-center justify-between p-2 rounded-md border bg-muted/50"
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                  <span className="text-sm truncate">
                                    {file.file.name}
                                  </span>
                                  <span className="text-xs text-muted-foreground flex-shrink-0">
                                    {formatFileSize(file.file.size)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-6 w-6 flex-shrink-0 hover:bg-primary/10 hover:text-primary"
                                    onClick={() => uploadFile(file.id)}
                                    disabled={
                                      isUploading || uploadingFileId === file.id
                                    }
                                  >
                                    {uploadingFileId === file.id ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      <Upload className="h-3 w-3" />
                                    )}
                                  </Button>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-6 w-6 flex-shrink-0 hover:bg-destructive/10 hover:text-destructive"
                                    onClick={() => removeFile(file.id)}
                                    disabled={
                                      isUploading || uploadingFileId === file.id
                                    }
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </>
                        )}
                      </div>

                      <div className="flex gap-2">
                        {/* <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex-1 text-xs"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={isUploading}
                        >
                          Add More Files
                        </Button> */}
                        {uploadedFiles.length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 text-xs"
                            onClick={uploadAllFiles}
                            disabled={isUploading || uploadedFiles.length === 0}
                          >
                            {isUploading ? (
                              <>
                                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                Uploading...
                              </>
                            ) : (
                              <>
                                <Upload className="mr-1 h-3 w-3" />
                                Upload All
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Generate Answer Button */}
                  <Button
                    className="w-full"
                    disabled={
                      isUploading ||
                      isGeneratingAnswers ||
                      isGeneratingQuestionAnswer ||
                      (!isKnowledgePalEnabled &&
                        (currentSelectedQuestion
                          ? !hasQuestionFiles
                          : existingFiles.length === 0)) ||
                      isRefetching
                    }
                    onClick={
                      currentSelectedQuestion
                        ? handleGenerateQuestionAnswer
                        : handleGenerateAnswers
                    }
                  >
                    {isGeneratingAnswers || isGeneratingQuestionAnswer ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : isRefetching ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Refreshing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        {currentSelectedQuestion
                          ? "Generate Answer"
                          : "Generate Answers for All"}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 text-primary animate-spin" />
                    <div className="text-center">
                      <h3 className="text-lg font-medium">Processing</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        Generating answers...
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {/* Single Question Answer Input - only shown when a specific question is selected */}
                  {currentSelectedQuestion && (
                    <div className="space-y-2">
                      {renderQuestionAnswer(
                        {
                          question_id: currentSelectedQuestion.id,
                          question_name: currentSelectedQuestion.name,
                          is_speculative: (
                            updatedTemplate?.sections
                              .find(
                                (s) =>
                                  s.heading === selectedSection ||
                                  s.section_id === selectedSection
                              )
                              ?.subsections.flatMap((sub) => sub.questions)
                              .find(
                                (q) =>
                                  q.question_id === currentSelectedQuestion.id
                              ) as Question | undefined
                          )?.is_speculative,
                        },
                        0
                      )}
                    </div>
                  )}

                  {/* Questions List with Answer Inputs - only shown when viewing a section */}
                  {selectedSection && !currentSelectedQuestion && (
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-muted-foreground">
                        {selectedSection}
                      </h3>

                      {updatedTemplate?.sections
                        .find((s) => s.heading === selectedSection)
                        ?.subsections.map((subsection, subsectionIndex) => {
                          const acceptedQuestions = subsection.questions.filter(
                            (q) => q.is_accepted
                          );
                          if (acceptedQuestions.length === 0) return null;

                          return (
                            <div
                              key={`subsection-${subsection.subheading}-${subsectionIndex}`}
                              className="space-y-3"
                            >
                              <h4 className="text-sm font-medium border-l-2 border-primary pl-2">
                                {subsection.subheading}
                              </h4>

                              <div className="space-y-3 pl-3">
                                {acceptedQuestions.map(
                                  (question, questionIndex) => (
                                    <div
                                      key={`${question.question_id}-${subsectionIndex}-${questionIndex}`}
                                      className="space-y-2"
                                    >
                                      {renderQuestionAnswer(
                                        {
                                          question_id: question.question_id,
                                          question_name: question.question_name,
                                          is_speculative: (question as Question)
                                            .is_speculative,
                                        },
                                        questionIndex
                                      )}
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  )}
                </>
              )}
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="p-4 border-t bg-background">
            <Button
              className="w-full"
              onClick={handleSave}
              disabled={
                isProcessing ||
                isSavingAnswers ||
                Object.keys(editedAnswers).length === 0
              }
            >
              {isSavingAnswers ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Answer"
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default AnswerGenerationSidebar;
