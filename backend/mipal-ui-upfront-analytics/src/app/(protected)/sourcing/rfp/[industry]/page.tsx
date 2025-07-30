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

interface Question {
  id: string;
  question: string;
  answer: string;
  section: string;
  references?: string[];
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

// Define an interface for the mock answers
interface IndustryAnswers {
  [key: string]: string;
}

interface MockAnswers {
  [industry: string]: IndustryAnswers;
}


// Define interfaces for references
interface IndustryReferences {
  [key: string]: string[];
}

interface MockReferences {
  [industry: string]: IndustryReferences;
}


export default function IndustryTemplatePage() {
  const params = useParams();
  const industry = params?.industry as string;
  
  // Don't use the API, use localStorage and dummy data
  const [templates, setTemplates] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<any>(null);
  
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Dummy data based on industry
  const getDummyQuestions = (industryName: string): Question[] => {
    switch(industryName.toLowerCase()) {
      case 'logistics':
        return [
          {
            id: "1",
            question: "What is the estimated volume of goods to be transported monthly?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "2",
            question: "What are the key delivery locations?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "3",
            question: "What are the specific transportation requirements?",
            answer: "",
            section: "Scope of Work",
          },
          {
            id: "4",
            question: "What are the delivery time expectations?",
            answer: "",
            section: "Scope of Work",
          },
          {
            id: "5",
            question: "What type of vehicles are required?",
            answer: "",
            section: "Technical Requirements",
          },
          {
            id: "6",
            question: "What are the insurance requirements?",
            answer: "",
            section: "Technical Requirements",
          },
        ];
      case 'software':
        return [
          {
            id: "1",
            question: "What is the scope of the software project?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "2",
            question: "What are the key features required?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "3",
            question: "What tech stack do you prefer?",
            answer: "",
            section: "Technical Requirements",
          },
          {
            id: "4",
            question: "What is the timeline for project completion?",
            answer: "",
            section: "Timeline",
          },
          {
            id: "5",
            question: "What are your testing requirements?",
            answer: "",
            section: "Technical Requirements",
          },
          {
            id: "6",
            question: "What is your budget range?",
            answer: "",
            section: "Budget",
          },
        ];
      case 'construction':
        return [
          {
            id: "1",
            question: "What is the scope of the construction project?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "2",
            question: "What are the material requirements?",
            answer: "",
            section: "Materials",
          },
          {
            id: "3",
            question: "What permits are needed?",
            answer: "",
            section: "Regulations",
          },
          {
            id: "4",
            question: "What is the timeline for project completion?",
            answer: "",
            section: "Timeline",
          },
          {
            id: "5",
            question: "What are your safety requirements?",
            answer: "",
            section: "Safety",
          },
          {
            id: "6",
            question: "What is your budget range?",
            answer: "",
            section: "Budget",
          },
        ];
      default:
        return [
          {
            id: "1",
            question: "What is the scope of your project?",
            answer: "",
            section: "Project Overview",
          },
          {
            id: "2",
            question: "What are your key requirements?",
            answer: "",
            section: "Requirements",
          },
          {
            id: "3",
            question: "What is your timeline?",
            answer: "",
            section: "Timeline",
          },
          {
            id: "4",
            question: "What is your budget?",
            answer: "",
            section: "Budget",
          },
        ];
    }
  };

  // Load template and questions from localStorage instead of API
  useEffect(() => {
    // Simulate API loading delay
    const timer = setTimeout(() => {
      try {
        // Get saved template from localStorage
        const savedTemplate = localStorage.getItem(`rfp_template_${industry}`);
        const templateData = savedTemplate ? JSON.parse(savedTemplate) : null;
        
        // Get saved questions from localStorage or generate dummy questions
        const savedQuestions = localStorage.getItem(`rfp_questions_${industry}`);
        const questionsData = savedQuestions 
          ? JSON.parse(savedQuestions) 
          : getDummyQuestions(industry);
        
        // Set template data
        setTemplates(templateData ? [templateData] : []);
        
        // Set questions data
        setQuestions(questionsData);
        
        setIsLoading(false);
      } catch (err) {
        console.error("Error loading template data", err);
        setError(err);
        setIsLoading(false);
        
        // Fallback to dummy questions
        setQuestions(getDummyQuestions(industry));
      }
    }, 800); // Simulate loading delay
    
    return () => clearTimeout(timer);
  }, [industry]);


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

  if (error || !templates || templates.length === 0) {
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

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-center py-8 space-y-8">
        <PageHeader
          title={templates[0]?.name || `${industry.charAt(0).toUpperCase() + industry.slice(1)} RFP Template`}
          description={templates[0]?.description || `Complete your RFP for ${industry} services by answering the questions below.`}
        />

        <div className="flex justify-end w-full space-x-4">
          <Button
            variant="outline"
            // onClick={handleGenerateAnswers}
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
      </div>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-[800px] sm:max-w-[800px]">
          <SheetHeader>
            <SheetTitle>{selectedQuestion?.question}</SheetTitle>
          </SheetHeader>
          
          <div className="flex h-[calc(100vh-200px)] mt-6">
            {/* Answer Section */}
            <div className="flex-1 pr-4 border-r">
              <h3 className="text-lg font-semibold mb-4">Answer</h3>
              <div className="h-[calc(100%-2rem)]">
                <Input
                  value={selectedQuestion?.answer || ""}
                  onChange={(e) => {
                    if (selectedQuestion) {
                      setQuestions(questions.map(q =>
                        q.id === selectedQuestion.id
                          ? { ...q, answer: e.target.value }
                          : q
                      ));
                      setSelectedQuestion({
                        ...selectedQuestion,
                        answer: e.target.value,
                      });
                    }
                  }}
                  placeholder="Enter your answer here..."
                  className="min-h-[300px] resize-y w-full h-full"
                />
              </div>
            </div>

            {/* References Section */}
            <div className="flex-1 pl-4">
              <h3 className="text-lg font-semibold mb-4">Reference Documents</h3>
              <div className="h-[calc(100%-2rem)] overflow-y-auto">
                {selectedQuestion?.references && selectedQuestion.references.length > 0 ? (
                  <ul className="space-y-2">
                    {selectedQuestion.references.map((ref, index) => (
                      <li key={index} className="flex items-center gap-2 p-2 hover:bg-muted/50 rounded-md cursor-pointer">
                        <FileText className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">{ref}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No references available</p>
                )}
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
} 