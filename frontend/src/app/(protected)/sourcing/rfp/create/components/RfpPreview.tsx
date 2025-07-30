"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, Eye, Download, FileText } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { format } from "date-fns";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import StreamingRichTextEditor from "./StreamingRichTextEditor";
import PdfDownloader from "./PdfDownloader";
import DocDownloader from "./DocDownloader";

interface RfpPreviewProps {
  templateId: string;
}

export default function RfpPreview({ templateId }: RfpPreviewProps) {
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [showPreviewContent, setShowPreviewContent] = useState(false);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const streamRef = useRef<AbortController | null>(null);
  const [viewMode, setViewMode] = useState<"edit" | "a4">("edit");
  const rawHtmlContentRef = useRef<string>("");

  const [previewFormData, setPreviewFormData] = useState({
    client_name: "",
    company_name: "",
    date: format(new Date(), "yyyy-MM-dd"),
    project_title: "",
  });

  const handlePreviewFormChange = (field: string, value: string) => {
    setPreviewFormData({
      ...previewFormData,
      [field]: value,
    });
  };

  const handleGeneratePreview = async () => {
    if (!templateId) return;

    setPreviewDialogOpen(false);
    setShowPreviewContent(true);
    setPreviewContent("");
    rawHtmlContentRef.current = ""; // Reset the raw HTML content
    setIsGeneratingPreview(true);

    console.log("Starting preview generation...");

    try {
      streamRef.current = new AbortController();
      const apiUrl = `/api/proxy/sourcing/rfp/documents/generate-stream`;

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          metadata: previewFormData,
          template_id: templateId,
        }),
        signal: streamRef.current.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to generate preview: ${response.status} ${errorText}`
        );
      }

      if (!response.body) {
        throw new Error("No response body available for streaming");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          if (!event.trim()) continue;

          const lines = event.split("\n");
          if (lines.length < 2) continue;

          const eventType = lines[0].replace("event: ", "");
          const dataLine = lines[1];

          if (dataLine && dataLine.startsWith("data: ")) {
            try {
              const data = JSON.parse(dataLine.replace("data: ", ""));

              switch (eventType) {
                case "document_start":
                  console.log(
                    "Document generation started:",
                    data.document?.id
                  );
                  break;
                case "content_block_start":
                  break;
                case "content_block_delta":
                  if (data.delta?.text) {
                    console.log(
                      "Received HTML chunk:",
                      data.delta.text.substring(0, 100) + "..."
                    );
                    // Accumulate raw HTML content in the ref
                    rawHtmlContentRef.current += data.delta.text;
                    setPreviewContent((prev) => prev + data.delta.text);
                  }
                  break;
                case "document_delta":
                  break;
                case "document_stop":
                  console.log("Document generation completed");
                  console.log(
                    "Final HTML content length:",
                    rawHtmlContentRef.current.length
                  );
                  setIsGeneratingPreview(false);
                  break;
                default:
                  console.log("Unhandled event type:", eventType, data);
              }
            } catch (e) {
              console.error(
                "Error parsing event data:",
                e,
                "for event line:",
                dataLine
              );
            }
          }
        }
      }
    } catch (error: any) {
      console.error("Error generating preview:", error);

      toast({
        title: "Failed to generate preview",
        description: error.message || "Please try again later",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingPreview(false);
      // Ensure the editor is focused after generation
      setTimeout(() => {
        const editorElement = document.querySelector(".ProseMirror");
        if (editorElement) {
          (editorElement as HTMLElement).focus();
        }
      }, 100); // Slight delay to ensure DOM is updated
    }
  };

  const cancelPreviewGeneration = () => {
    // Abort the fetch request if it's in progress
    if (streamRef.current) {
      streamRef.current.abort();
      streamRef.current = null;
    }

    setShowPreviewContent(false);
    setIsGeneratingPreview(false);
    toast({
      title: "Preview generation cancelled",
    });
  };

  return (
    <>
      <Button className="gap-2" onClick={() => setPreviewDialogOpen(true)}>
        <FileText className="h-4 w-4" />
        Preview
      </Button>

      {/* Preview Dialog */}
      <Dialog open={previewDialogOpen} onOpenChange={setPreviewDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Preview RFP Document</DialogTitle>
            <DialogDescription>
              Enter information about the RFP to generate a preview.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="client_name" className="text-right">
                Client Name
              </Label>
              <Input
                id="client_name"
                value={previewFormData.client_name}
                onChange={(e) =>
                  handlePreviewFormChange("client_name", e.target.value)
                }
                className="col-span-3"
                placeholder="XYZ Corp"
              />
            </div> */}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="company_name" className="text-left leading-4">
                Company Name
              </Label>
              <Input
                id="company_name"
                value={previewFormData.company_name}
                onChange={(e) =>
                  handlePreviewFormChange("company_name", e.target.value)
                }
                className="col-span-3"
                placeholder="Acme Inc."
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="date" className="text-left leading-4">
                Date
              </Label>
              <Input
                id="date"
                type="date"
                value={previewFormData.date}
                onChange={(e) =>
                  handlePreviewFormChange("date", e.target.value)
                }
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="project_title" className="text-left leading-4">
                Project Title
              </Label>
              <Input
                id="project_title"
                value={previewFormData.project_title}
                onChange={(e) =>
                  handlePreviewFormChange("project_title", e.target.value)
                }
                className="col-span-3"
                placeholder="Software Development Project"
              />
            </div>
          </div>
          <DialogFooter>
            {/* <Button variant="outline" onClick={() => setPreviewDialogOpen(false)}>
              Cancel
            </Button> */}
            <Button onClick={handleGeneratePreview}>Continue</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Content Dialog */}
      <Dialog
        open={showPreviewContent}
        onOpenChange={(open) => {
          if (!open && !isGeneratingPreview) {
            setShowPreviewContent(false);
          } else if (!open && isGeneratingPreview) {
            cancelPreviewGeneration();
          }
        }}
      >
        <DialogContent className="sm:max-w-[90%] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>RFP Preview</span>
            </DialogTitle>
            <DialogDescription>
              {isGeneratingPreview
                ? "Generating RFP document..."
                : "Preview of your generated RFP document."}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-auto min-h-[60vh]">
            <StreamingRichTextEditor
              content={
                isGeneratingPreview ? previewContent : rawHtmlContentRef.current
              }
              onChange={setPreviewContent}
              streaming={isGeneratingPreview}
              readOnly={isGeneratingPreview}
              a4View={viewMode === "a4"}
              streamRef={streamRef}
              onAbort={cancelPreviewGeneration}
              height="60vh"
            />
          </div>
          <DialogFooter className="flex flex-col sm:flex-row sm:justify-between w-full gap-2">
            <Button
              variant="outline"
              onClick={() => setShowPreviewContent(false)}
              disabled={isGeneratingPreview}
            >
              Close
            </Button>
            <div className="flex gap-2">
              {!isGeneratingPreview && previewContent && (
                <>
                  <PdfDownloader
                    rawHtmlContent={rawHtmlContentRef.current}
                    previewFormData={previewFormData}
                  />
                  <DocDownloader
                    rawHtmlContent={rawHtmlContentRef.current}
                    previewFormData={previewFormData}
                  />
                </>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
