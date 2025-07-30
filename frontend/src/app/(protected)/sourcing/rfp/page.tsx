"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";
import {
  Building2,
  Truck,
  Laptop,
  FileText,
  Edit2,
  Save,
  Upload,
  X,
  Download,
  FileType,
  ChevronLeft,
  Home,
  ChevronRight,
  Plus,
  Loader2,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetAllRfpTemplatesQuery,
  useDownloadTemplateMutation,
  useUploadTemplateMutation,
  useUpdateTemplateNameMutation,
} from "@/store/services/sourcingApi";
import { TemplateSelectionPanel } from "./components/TemplateSelectionPanel";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "@/hooks/use-toast";

interface TemplateSection {
  heading: string;
  subheadings: string[];
}

const defaultTemplateSections: TemplateSection[] = [
  {
    heading: "Project Overview",
    subheadings: ["Volume", "Locations", "Timeline"],
  },
  {
    heading: "Scope of Work",
    subheadings: ["Requirements", "Deliverables", "Constraints"],
  },
  {
    heading: "Technical Requirements",
    subheadings: ["Equipment", "Standards", "Compliance"],
  },
];

// Add this function before the RFPPage component
const getFileIcon = (fileName: string) => {
  const extension = fileName.split(".").pop()?.toLowerCase();

  switch (extension) {
    case "pdf":
      return { icon: FileText, color: "text-red-600 dark:text-red-400" };
    case "doc":
    case "docx":
      return { icon: FileText, color: "text-blue-600 dark:text-blue-400" };
    case "md":
    case "markdown":
      return {
        icon: FileText,
        color: "text-emerald-600 dark:text-emerald-400",
      };
    default:
      return { icon: FileType, color: "text-gray-600 dark:text-gray-400" };
  }
};

export default function RFPPage() {
  const router = useRouter();
  const {
    data: templatesData,
    isLoading: isLoadingAllTemplates,
    error: allTemplatesError,
  } = useGetAllRfpTemplatesQuery();
  console.log("templatesData", templatesData);
  const [downloadTemplate] = useDownloadTemplateMutation();
  const [uploadTemplate] = useUploadTemplateMutation();
  const [updateTemplateName] = useUpdateTemplateNameMutation();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [sections, setSections] = useState<TemplateSection[]>(
    defaultTemplateSections
  );
  const [isTemplatePanelOpen, setIsTemplatePanelOpen] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [selectedSavedTemplate, setSelectedSavedTemplate] = useState<
    any | null
  >(null);
  const [uploadResponse, setUploadResponse] = useState<any>(null);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [templateNameInput, setTemplateNameInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);
  const [isSavingTemplateName, setIsSavingTemplateName] = useState(false);

  // Convert API template sections to our format
  const convertApiSections = (apiSections: any[]) => {
    return apiSections.map((section) => ({
      heading: section.heading,
      subheadings: [section.subheading],
    }));
  };

  // Effect to update sections when template is selected
  useEffect(() => {
    if (
      selectedTemplate &&
      selectedIndustry &&
      templatesData?.[selectedIndustry]
    ) {
      const template = templatesData[selectedIndustry].find(
        (t) => t.id === selectedTemplate
      );
      if (template) {
        setSections(convertApiSections(template.sections));
        setTemplateName(template.name);
      }
    }
  }, [selectedTemplate, selectedIndustry, templatesData]);

  // Update templateNameInput when uploadResponse changes
  useEffect(() => {
    if (uploadResponse?.name) {
      setTemplateNameInput(uploadResponse.name);
    }
  }, [uploadResponse]);

  const handleTemplateClick = (id: string, industry: string) => {
    setSelectedTemplate(id);
    setSelectedIndustry(industry);
    setIsDialogOpen(true);
    setIsEditing(false);

    // Clear previous template data
    setTemplateName("");
    setSections(defaultTemplateSections);
  };

  const handleTemplateSelect = () => {
    if (selectedIndustry) {
      // Save selected template data to localStorage
      const templateToSave = templatesData?.[selectedIndustry]?.find(
        (t) => t.id === selectedTemplate
      );

      if (templateToSave) {
        // Store the template data in localStorage for the industry page to use
        localStorage.setItem(
          `rfp_template_${selectedIndustry}`,
          JSON.stringify(templateToSave)
        );

        // Also store questions based on template sections
        const dummyQuestions = templateToSave.sections.map(
          (section: any, index: number) => ({
            id: `${index + 1}`,
            question: `What are your requirements for ${section.subheading || section.heading}?`,
            answer: "",
            section: section.heading,
          })
        );
        localStorage.setItem(
          `rfp_questions_${selectedIndustry}`,
          JSON.stringify(dummyQuestions)
        );
      }

      // Navigate to the industry page with template ID
      router.push(
        `/sourcing/rfp/${selectedIndustry}?template_id=${selectedTemplate}`
      );
    }
  };

  const handleSaveTemplate = async () => {
    setIsSavingTemplate(true);
    try {
      // Save the customized template to localStorage
      const savedTemplates = JSON.parse(
        localStorage.getItem("customTemplates") || "[]"
      );
      savedTemplates.push({
        id: `custom-${Date.now()}`,
        name: templateName,
        sections,
      });
      localStorage.setItem("customTemplates", JSON.stringify(savedTemplates));
      setIsEditing(false);
    } catch (error) {
      console.error("Error saving template:", error);
      toast({
        title: "Error",
        description: "Failed to save template. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSavingTemplate(false);
    }
  };

  const handleAddSection = () => {
    setSections([...sections, { heading: "", subheadings: [""] }]);
  };

  const handleUpdateSection = (
    index: number,
    field: "heading" | "subheadings",
    value: string | string[]
  ) => {
    const newSections = [...sections];
    newSections[index] = { ...newSections[index], [field]: value };
    setSections(newSections);
  };

  const handleAddSubheading = (sectionIndex: number) => {
    const newSections = [...sections];
    newSections[sectionIndex].subheadings.push("");
    setSections(newSections);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check file type
      const validTypes = [".docx", ".doc", ".md", ".markdown"];
      const fileExt = file.name
        .substring(file.name.lastIndexOf("."))
        .toLowerCase();

      if (!validTypes.includes(fileExt)) {
        toast({
          title: "Invalid File Type",
          description: "Please upload a  DOCX, MD, or MARKDOWN file.",
          variant: "destructive",
        });
        return;
      }

      // Check file size (limit to 2MB)
      if (file.size > 2 * 1024 * 1024) {
        toast({
          title: "File Too Large",
          description: "File size should be less than 2MB.",
          variant: "destructive",
        });
        return;
      }

      setUploadedFile(file);
      setSelectedSavedTemplate(null);
    }
  };

  const clearFileUpload = () => {
    setUploadedFile(null);
    // Reset the file input
    const fileInput = document.getElementById(
      "template-upload"
    ) as HTMLInputElement;
    if (fileInput) fileInput.value = "";
  };

  const handleSavedTemplateSelect = (template: any) => {
    setSelectedSavedTemplate(template);
    setUploadedFile(null);
    setIsTemplatePanelOpen(false);
  };

  const handleContinue = async () => {
    if (uploadedFile) {
      try {
        setIsProcessing(true);

        // Create form data manually
        const formData = new FormData();
        formData.append("file", uploadedFile);
        formData.append("name", "");

        // Use the RTK Query mutation directly
        const result = await uploadTemplate(uploadedFile).unwrap();

        // Handle successful response
        setUploadResponse(result);
        setTemplateNameInput(result.name || "");
        setIsUploadDialogOpen(true);
      } catch (error: any) {
        console.error("Error uploading template:", error);

        // Assuming error has a structure with title and message
        const title = error.response?.detail?.title || "Upload Failed";
        const description =
          error.response?.detail?.message || "An unexpected error occurred";

        toast({
          title: title,
          description: description,
          variant: "destructive",
        });
      } finally {
        setIsProcessing(false);
      }
    } else if (selectedSavedTemplate) {
      try {
        setIsProcessing(true);
        // Handle saved template selection - navigate with template ID if available
        if (selectedSavedTemplate.id) {
          await router.push(
            `/sourcing/rfp/create?template_id=${selectedSavedTemplate.id}`
          );
        } else {
          await router.push("/sourcing/rfp/create");
        }
      } catch (error) {
        toast({
          title: "Navigation Failed",
          description:
            "Failed to navigate to template creation. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsProcessing(false);
      }
    }
  };

  // Function to save the template name
  const handleSaveTemplateName = async () => {
    if (uploadResponse?.template_id && templateNameInput) {
      setIsSavingTemplateName(true);
      try {
        await updateTemplateName({
          templateId: uploadResponse.template_id,
          name: templateNameInput,
        }).unwrap();

        toast({
          title: "Template Name Updated",
          description: "Template name updated successfully",
        });
        setIsUploadDialogOpen(false);

        // Navigate to create page with template ID
        router.push(
          `/sourcing/rfp/create?template_id=${uploadResponse.template_id}`
        );
      } catch (error) {
        console.error("Error updating template name:", error);
        toast({
          title: "Error",
          description: "Failed to update template name",
          variant: "destructive",
        });
      } finally {
        setIsSavingTemplateName(false);
      }
    } else {
      setIsUploadDialogOpen(false);
      // If there's a template ID but no name update, still include template ID in URL
      if (uploadResponse?.template_id) {
        router.push(
          `/sourcing/rfp/create?template_id=${uploadResponse.template_id}`
        );
      } else {
        router.push("/sourcing/rfp/create");
      }
    }
  };

  const handleDownload = async (format: string) => {
    try {
      const response = await downloadTemplate(format).unwrap();

      // Create a blob URL for the file
      const blob = new Blob([response], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);

      // Create a temporary link element
      const link = document.createElement("a");
      link.href = url;
      link.download = `rfp_template.${format}`;

      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the blob URL
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading template:", error);
      toast({
        title: "Error",
        description: "Failed to download template",
        variant: "destructive",
      });
    }
  };

  if (isLoadingAllTemplates) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          {/* Breadcrumb Skeleton */}
          <div className="flex items-center gap-4 w-full">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-8 w-32" />
            </div>
          </div>

          {/* Page Header Skeleton */}
          <div className="flex justify-between items-center w-full">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <Skeleton className="h-10 w-40" />
          </div>

          {/* Template Selection Options Skeleton */}
          <div className="w-full space-y-8">
            {/* Upload Template Card Skeleton */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-4 w-64" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full rounded-lg" />
              </CardContent>
            </Card>

            {/* Saved Templates Card Skeleton */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-4 w-64" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-10 w-full" />
              </CardContent>
            </Card>

            {/* Divider Skeleton */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t"></div>
              </div>
              <div className="relative flex justify-center">
                <Skeleton className="h-4 w-48" />
              </div>
            </div>
          </div>

          {/* Industry Templates Grid Skeleton */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-2 w-full">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-12 w-12 rounded-lg" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Skeleton className="h-4 w-full" />
                  <div className="space-y-2">
                    {[1, 2, 3].map((j) => (
                      <Skeleton key={j} className="h-4 w-3/4" />
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (allTemplatesError) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          <PageHeader
            title="RFP Templates"
            description="An error occurred while loading templates"
          />
          <div className="text-red-500">
            Failed to load RFP templates. Please try again later.
          </div>
        </div>
      </div>
    );
  }

  // Get industry icons
  const getIndustryIcon = (industry: string) => {
    switch (industry) {
      case "logistics":
        return Truck;
      case "software":
        return Laptop;
      case "construction":
        return Building2;
      default:
        return FileText;
    }
  };

  // Get industry colors
  const getIndustryColor = (industry: string) => {
    switch (industry) {
      case "logistics":
        return "text-blue-500";
      case "software":
        return "text-green-500";
      case "construction":
        return "text-orange-500";
      default:
        return "text-purple-500";
    }
  };

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-center py-8 space-y-8">
        <div className="flex flex-col w-full space-y-4">
          {/* Breadcrumb and Back Button Section */}
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => router.back()}
              className="h-10 w-10 hover:bg-accent"
              title="Go back"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-2 text-sm">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 hover:bg-accent"
                onClick={() => router.push("/")}
              >
                <Home className="h-4 w-4 mr-1" />
                Home
              </Button>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 hover:bg-accent"
                onClick={() => router.push("/sourcing")}
              >
                Sourcing
              </Button>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-primary">RFP Templates</span>
            </div>
          </div>

          {/* Page Header Section */}
          <div className="flex justify-between items-center w-full">
            <div className="flex flex-col gap-1">
              <h1 className="text-2xl font-bold tracking-tight">
                RFP Templates
              </h1>
              <p className="text-sm text-muted-foreground">
                create an RFP template to get started with your sourcing process
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="flex items-center gap-2"
                onClick={() => setIsTemplatePanelOpen(true)}
              >
                <FileText className="w-4 h-4" />
                History
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="flex items-center gap-2">
                    <Download className="w-4 h-4" />
                    Download Sample
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleDownload("docx")}>
                    .docx{" "}
                    <span className="text-xs text-muted-foreground">
                      (Preferred)
                    </span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleDownload("md")}>
                    .md
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled
                    onClick={() => handleDownload("pdf")}
                  >
                    .pdf
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled
                    onClick={() => handleDownload("markdown")}
                  >
                    .markdown
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Template Selection Options */}
        <div className="w-full space-y-8">
          {/* Option 1: Upload Template */}
          <Card
            className={`relative transition-all duration-200 ${selectedSavedTemplate ? "opacity-50 pointer-events-none" : ""}`}
          >
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900">
                  <Upload className="w-6 h-6 text-blue-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    Upload Your Template
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Upload your own RFP template file
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-center w-full">
                  <label
                    htmlFor="template-upload"
                    className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${!uploadedFile ? "hover:bg-muted/50" : "bg-muted/30"}`}
                  >
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      {!uploadedFile ? (
                        <>
                          <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                          <p className="mb-2 text-sm text-muted-foreground">
                            <span className="font-semibold">
                              Click to upload
                            </span>{" "}
                            or drag and drop
                          </p>
                          <p className="text-xs text-muted-foreground">
                            DOCX, MD, MARKDOWN only (max 10MB)
                          </p>
                        </>
                      ) : (
                        <div className="flex flex-col items-center text-center">
                          <div
                            className={`flex items-center gap-2 ${getFileIcon(uploadedFile.name).color}`}
                          >
                            {(() => {
                              const { icon: Icon } = getFileIcon(
                                uploadedFile.name
                              );
                              return <Icon className="w-6 h-6" />;
                            })()}
                            <span className="font-medium text-sm">
                              {uploadedFile.name}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {(uploadedFile.size / 1024).toFixed(1)} KB · Click
                            to change file
                          </p>
                        </div>
                      )}
                    </div>
                    <input
                      id="template-upload"
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.doc,.md,.markdown"
                      onChange={handleFileUpload}
                      disabled={!!selectedSavedTemplate}
                    />
                  </label>
                </div>
                {uploadedFile && (
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearFileUpload}
                      className="gap-2"
                    >
                      <X className="w-3.5 h-3.5" />
                      Remove file
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Option 2: Choose from Saved Templates */}
          {/* <Card
            className={`relative transition-all duration-200 ${uploadedFile ? "opacity-50 pointer-events-none" : ""}`}
          >
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900">
                  <FileText className="w-6 h-6 text-green-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    Choose from Saved RFPs
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Select from your previously saved RFPs
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Button
                  variant="outline"
                  className="w-full"
                  // onClick={() => setIsTemplatePanelOpen(true)}
                  disabled={!!uploadedFile}
                >
                  Browse RFPs
                </Button>
                {selectedSavedTemplate && (
                  <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">
                        {selectedSavedTemplate.name}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setSelectedSavedTemplate(null)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card> */}

          {/* Continue Button */}
          {(uploadedFile || selectedSavedTemplate) && (
            <div className="flex justify-end">
              <Button
                onClick={handleContinue}
                size="lg"
                disabled={isProcessing}
                className="min-w-[100px]"
              >
                {isProcessing ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </div>
                ) : (
                  "Continue"
                )}
              </Button>
            </div>
          )}

          {/* Divider with "OR" */}
          {/* <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or select from industry templates
              </span>
            </div>
          </div> */}
        </div>

        {/* <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-2 w-full">
        
          {templatesData &&
            Object.entries(templatesData).map(([industry, templates]) => {
              const Icon = getIndustryIcon(industry);
              const color = getIndustryColor(industry);

              return (
                <div key={industry} className="space-y-4">

                  <div className="grid grid-cols-1 gap-4">
                    {templates.map((template) => (
                      <Card
                        key={template.id}
                        className="cursor-pointer hover:scale-[101%] hover:shadow-md active:scale-[100%] active:shadow-sm transition-all duration-200"
                        onClick={() =>
                          handleTemplateClick(template.id, industry)
                        }
                      >
                        <CardHeader>
                          <div className="flex items-center gap-4">
                            <div className={`p-2 rounded-lg ${color}`}>
                              <Icon className="w-6 h-6" />
                            </div>
                            <CardTitle className="text-lg">
                              {template.name}
                            </CardTitle>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">
                            {template.description}
                          </p>
                          <div className="mt-4 space-y-2">
                            {template?.sections?.map((section, index) => (
                              <div key={index} className="text-sm">
             
                                <p className="text-muted-foreground">
                                  {section.subheading}
                                </p>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              );
            })}
        </div> */}

        {/* Template Selection Panel */}
        <TemplateSelectionPanel
          isOpen={isTemplatePanelOpen}
          onClose={() => setIsTemplatePanelOpen(false)}
          onSelectTemplate={handleSavedTemplateSelect}
        />

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="w-[70vw] h-[70vh] max-w-[70vw] max-h-[70vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-xl font-semibold flex items-center gap-2">
                {selectedTemplate ? (
                  <>
                    <FileText className="w-5 h-5 text-primary" />
                    {selectedTemplate}
                  </>
                ) : (
                  "Template Preview"
                )}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-6">
              {isEditing ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Template Name</Label>
                    <Input
                      value={templateName}
                      onChange={(e) => setTemplateName(e.target.value)}
                      placeholder="Enter template name"
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-4">
                    {sections.map((section, sectionIndex) => (
                      <div
                        key={sectionIndex}
                        className="space-y-3 p-4 border rounded-lg bg-card"
                      >
                        <div className="space-y-2">
                          <Label className="text-sm font-medium">
                            Section Heading
                          </Label>
                          <Input
                            value={section.heading}
                            onChange={(e) =>
                              handleUpdateSection(
                                sectionIndex,
                                "heading",
                                e.target.value
                              )
                            }
                            placeholder="Enter section heading"
                            className="h-10"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-sm font-medium">
                            Subheadings
                          </Label>
                          {section.subheadings.map((subheading, subIndex) => (
                            <div
                              key={subIndex}
                              className="flex items-center gap-2"
                            >
                              <Input
                                value={subheading}
                                onChange={(e) => {
                                  const newSubheadings = [
                                    ...section.subheadings,
                                  ];
                                  newSubheadings[subIndex] = e.target.value;
                                  handleUpdateSection(
                                    sectionIndex,
                                    "subheadings",
                                    newSubheadings
                                  );
                                }}
                                placeholder="Enter subheading"
                                className="h-10"
                              />
                              {subIndex === section.subheadings.length - 1 && (
                                <Button
                                  variant="outline"
                                  size="icon"
                                  onClick={() =>
                                    handleAddSubheading(sectionIndex)
                                  }
                                  className="h-10 w-10"
                                >
                                  <Plus className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      onClick={handleAddSection}
                      className="w-full h-10"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Section
                    </Button>
                  </div>
                  <div className="flex justify-end space-x-2 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => setIsEditing(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveTemplate}
                      className="gap-2"
                      disabled={isSavingTemplate}
                    >
                      {isSavingTemplate ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4" />
                          Save Template
                        </>
                      )}
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-4">
                    {sections.map((section, index) => (
                      <div
                        key={index}
                        className="space-y-3 p-4 border rounded-lg bg-card"
                      >
                        <h4 className="font-medium text-lg">
                          {section.heading}
                        </h4>
                        <ul className="space-y-2">
                          {section.subheadings.map((subheading, subIndex) => (
                            <li
                              key={subIndex}
                              className="flex items-center gap-2 text-muted-foreground"
                            >
                              <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                              {subheading}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-end space-x-2 pt-4 border-t">
                    <Button
                      variant="outline"
                      onClick={() => setIsDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setIsEditing(true)}
                      className="gap-2"
                    >
                      <Edit2 className="w-4 h-4" />
                      Edit Template
                    </Button>
                    <Button onClick={handleTemplateSelect} className="gap-2">
                      <FileText className="w-4 h-4" />
                      Use Template
                    </Button>
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>

        {/* Upload Response Dialog */}
        <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
          <DialogContent className="max-w-2xl flex flex-col h-[80vh]">
            <DialogHeader className="px-4 py-2 border-b">
              <DialogTitle className="text-xl font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                Template Preview
              </DialogTitle>
            </DialogHeader>
            {uploadResponse && (
              <>
                <div className="p-4 border-b">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Template Name</Label>
                    <Input
                      id="template-name"
                      value={templateNameInput}
                      onChange={(e) => setTemplateNameInput(e.target.value)}
                      placeholder="Enter template name"
                      className="h-10"
                    />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  <div className="space-y-4">
                    {uploadResponse.sections.map(
                      (section: any, index: number) => (
                        <div
                          key={index}
                          className="p-4 border rounded-lg bg-card"
                        >
                          <h4 className="font-medium text-lg mb-3">
                            {section.heading}
                          </h4>
                          <div className="space-y-2">
                            {section.subsections.map(
                              (subsection: any, subIndex: number) => (
                                <div
                                  key={subIndex}
                                  className="pl-4 flex items-center gap-2"
                                >
                                  <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                                  <p className="text-sm text-muted-foreground">
                                    {subsection.subheading}
                                  </p>
                                </div>
                              )
                            )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
                <div className="px-4 py-3 border-t flex justify-end space-x-2 bg-background">
                  <Button
                    variant="outline"
                    onClick={() => setIsUploadDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSaveTemplateName}
                    className="gap-2"
                    disabled={isSavingTemplateName || !templateNameInput}
                  >
                    {isSavingTemplateName ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Save
                      </>
                    )}
                  </Button>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
