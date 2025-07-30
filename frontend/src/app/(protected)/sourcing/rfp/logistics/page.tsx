"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { FileText, Save, Share2 } from "lucide-react";
import { Separator } from "@radix-ui/react-separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams } from "next/navigation";
import { useGetAllRfpTemplatesQuery } from "@/store/services/sourcingApi";

interface Question {
  id: string;
  question: string;
  answer: string;
  section: string;
}

// Generate questions based on template sections
const generateQuestionsFromTemplate = (template: any): Question[] => {
  if (!template || !template.sections) return [];
  
  return template.sections.map((section: any, index: number) => ({
    id: `${index + 1}`,
    question: `What are your requirements for ${section.subheading}?`,
    answer: "",
    section: section.heading,
  }));
};

const mockAnswers = {
  "1": "Approximately 500 tons of goods per month",
  "2": "Primary locations include Mumbai, Delhi, and Bangalore",
  "3": "Need temperature-controlled transportation for perishable goods",
  "4": "Standard delivery within 48 hours, express delivery within 24 hours",
  "5": "Refrigerated trucks with GPS tracking",
  "6": "Minimum coverage of $1 million per vehicle",
};

export default function LogisticsTemplatePage() {
  const params = useParams();
  const industry = (params?.industry as string) || "logistics";
  
  const { data: templates, isLoading, error } = useGetAllRfpTemplatesQuery();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateAnswers = () => {
    setIsGenerating(true);
    // Simulate API call
    setTimeout(() => {
      setQuestions(questions.map(q => ({
        ...q,
        answer: mockAnswers[q.id as keyof typeof mockAnswers] || ""
      })));
      setIsGenerating(false);
    }, 2000);
  };

  const handleQuestionClick = (question: Question) => {
    setSelectedQuestion(question);
    setIsSheetOpen(true);
  };

  const handleSave = () => {
    // Save to local storage for now
    localStorage.setItem(`rfp_${industry}`, JSON.stringify(questions));
  };

  const handleShare = () => {
    // Implement share functionality
    console.log(`Sharing RFP for ${industry}`);
  };

  if (isLoading) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          <Skeleton className="h-12 w-64" />
          <Skeleton className="h-6 w-full max-w-md" />
          <div className="space-y-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !templates || !templates[industry] || templates[industry].length === 0) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          <PageHeader
            title={`${industry.charAt(0).toUpperCase() + industry.slice(1)} RFP Template`}
            description="An error occurred while loading the template"
          />
          <div className="text-red-500">Failed to load template details. Please try again later.</div>
        </div>
      </div>
    );
  }

  const currentTemplate = templates[industry]?.[0];

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-center py-8 space-y-8">
        <PageHeader
          title={currentTemplate?.name || `${industry.charAt(0).toUpperCase() + industry.slice(1)} RFP Template`}
          description={currentTemplate?.description || `Complete your RFP for ${industry} services by answering the questions below.`}
        />

        <div className="flex justify-end w-full space-x-4">
          <Button
            variant="outline"
            onClick={handleGenerateAnswers}
            disabled={isGenerating}
          >
            {isGenerating ? "Generating..." : "Generate Answers"}
          </Button>
          <Button variant="outline" onClick={handleSave}>
            <Save className="w-4 h-4 mr-2" />
            Save
          </Button>
          <Button onClick={handleShare}>
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
        </div>

        <div className="w-full space-y-6">
          {questions.map((question, index) => (
            <div key={question.id} className="space-y-4">
              {index === 0 || questions[index - 1].section !== question.section ? (
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">{question.section}</h3>
                  <Separator />
                </div>
              ) : null}
              
              <div
                className="p-4 border rounded-lg cursor-pointer hover:bg-muted/50"
                onClick={() => handleQuestionClick(question)}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">
                      {question.question}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {question.answer || "Click to edit answer"}
                    </p>
                  </div>
                  <FileText className="w-4 h-4 text-muted-foreground" />
                </div>
              </div>
            </div>
          ))}
        </div>

        <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
          <SheetContent className="w-[70%] sm:max-w-[70%]">
            <SheetHeader>
            <SheetTitle>Edit Answer</SheetTitle>
            </SheetHeader>
            <div >
              {selectedQuestion && (
                <div className="flex h-[calc(100vh-8rem)]">
                  {/* Left Column - Edit Answer */}
                  <div className="flex-1 pr-4 space-y-4">
                    <div className="space-y-2">              
                      <Label>Question</Label>
                      <p className="text-sm">{selectedQuestion.question}</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Answer</Label>
                      <Input
                        value={selectedQuestion.answer}
                        onChange={(e) => {
                          setQuestions(questions.map(q =>
                            q.id === selectedQuestion.id
                              ? { ...q, answer: e.target.value }
                              : q
                          ));
                          setSelectedQuestion({
                            ...selectedQuestion,
                            answer: e.target.value,
                          });
                        }}
                      />
                    </div>
                  </div>

                  {/* Vertical Divider */}
                  <div className="w-px bg-border" />

                  {/* Right Column - Reference Documents */}
                  <div className="flex-1 pl-4 space-y-4">
                    <div className="space-y-2">
                      <Label>Reference Documents</Label>
                      <div className="p-4 border rounded-lg">
                        <p className="text-sm text-muted-foreground">
                          Sample Document 1.pdf
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Sample Document 2.pdf
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
} 