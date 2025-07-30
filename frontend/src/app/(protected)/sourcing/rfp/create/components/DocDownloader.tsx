import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { format } from "date-fns";

interface DocDownloaderProps {
  rawHtmlContent: string;
  previewFormData: {
    client_name: string;
    company_name: string;
    date: string;
    project_title: string;
  };
}

export default function DocDownloader({
  rawHtmlContent,
  previewFormData,
}: DocDownloaderProps) {
  const handleDownloadDoc = async () => {
    try {
      toast({
        title: "Preparing document",
        description: "Setting up your document for DOC export...",
      });

      // Load dependencies
      const {
        Document,
        Packer,
        Paragraph,
        TextRun,
        HeadingLevel,
        AlignmentType,
        Table,
        TableRow,
        TableCell,
        BorderStyle,
        LevelFormat,
        NumberFormat,
      } = await import("docx");

      // Process HTML content to extract structured data
      const processHtmlContent = () => {
        // Create a temporary div to parse the HTML
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = rawHtmlContent;

        // Clean up the HTML by removing unnecessary elements
        const emptyElements = tempDiv.querySelectorAll("div:empty, p:empty");
        emptyElements.forEach((el) => el.remove());

        return {
          element: tempDiv,
        };
      };

      // Track list instances to restart numbering for each new list
      let listInstanceCounter = 0;

      // Convert HTML elements to DOCX elements
      const convertHtmlToDocx = (element: HTMLElement): any[] => {
        const docxElements: any[] = [];

        // Process all child nodes
        Array.from(element.childNodes).forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            // Handle text nodes
            const text = node.textContent?.trim();
            if (text) {
              docxElements.push(
                new Paragraph({
                  children: [new TextRun(text)],
                })
              );
            }
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            const el = node as HTMLElement;

            // Handle different element types
            switch (el.tagName.toLowerCase()) {
              case "h1":
                // Check if this heading has a section ID that should start on a new page
                const headingId = el.getAttribute("id") || "";
                const shouldStartNewPage = headingId === "section-1";

                docxElements.push(
                  new Paragraph({
                    text: el.textContent || "",
                    heading: HeadingLevel.HEADING_1,
                    spacing: { before: 400, after: 200 },
                    pageBreakBefore: shouldStartNewPage,
                  })
                );
                break;

              case "h2":
                docxElements.push(
                  new Paragraph({
                    text: el.textContent || "",
                    heading: HeadingLevel.HEADING_2,
                    spacing: { before: 360, after: 200 },
                  })
                );
                break;

              case "h3":
                docxElements.push(
                  new Paragraph({
                    text: el.textContent || "",
                    heading: HeadingLevel.HEADING_3,
                    spacing: { before: 320, after: 200 },
                  })
                );
                break;

              case "p":
                docxElements.push(
                  new Paragraph({
                    children: [new TextRun(el.textContent || "")],
                    spacing: { after: 120 },
                  })
                );
                break;

              case "ul":
                const ulItems = Array.from(el.querySelectorAll(":scope > li"));
                processListItems(ulItems, docxElements, false, 0, null);
                break;

              case "ol":
                // Create a new instance ID for each ordered list to restart numbering
                listInstanceCounter++;
                const instanceId = `list-${listInstanceCounter}`;
                const olItems = Array.from(el.querySelectorAll(":scope > li"));
                processListItems(olItems, docxElements, true, 0, instanceId);
                break;

              case "table":
                try {
                  // Handle tables directly without explicit type annotations
                  const tableRows = el.querySelectorAll("tr");
                  const docRows = Array.from(tableRows)
                    .map((tr) => {
                      const tableCells = tr.querySelectorAll("td, th");
                      const docCells = Array.from(tableCells).map((td) => {
                        return new TableCell({
                          children: [new Paragraph(td.textContent || "")],
                          borders: {
                            top: { style: BorderStyle.SINGLE, size: 1 },
                            bottom: { style: BorderStyle.SINGLE, size: 1 },
                            left: { style: BorderStyle.SINGLE, size: 1 },
                            right: { style: BorderStyle.SINGLE, size: 1 },
                          },
                        });
                      });

                      return new TableRow({
                        children: docCells,
                      });
                    })
                    .filter((row) => row.CellCount > 0);

                  if (docRows.length > 0) {
                    docxElements.push(
                      new Table({
                        rows: docRows,
                        width: {
                          size: 100,
                          type: "pct",
                        },
                      })
                    );

                    // Add spacing after table
                    docxElements.push(
                      new Paragraph({
                        text: "",
                        spacing: { after: 200 },
                      })
                    );
                  }
                } catch (tableError) {
                  console.error("Error processing table:", tableError);
                  // Add a paragraph indicating table couldn't be processed
                  docxElements.push(
                    new Paragraph({
                      text: "[Table content]",
                      spacing: { after: 200 },
                    })
                  );
                }
                break;

              case "div":
                // Check if it's a centered div (cover page)
                if (
                  el.style.display === "flex" &&
                  el.style.flexDirection === "column" &&
                  el.style.alignItems === "center" &&
                  el.style.justifyContent === "center" &&
                  el.style.textAlign === "center"
                ) {
                  // This is likely a cover page, so add centered elements
                  Array.from(el.childNodes).forEach((childNode) => {
                    if (childNode.nodeType === Node.ELEMENT_NODE) {
                      const childEl = childNode as HTMLElement;
                      let text = childEl.textContent || "";

                      if (text.trim()) {
                        // Check if the text contains company name and date on the same line
                        if (
                          text.includes("Company:") &&
                          text.includes("Date:")
                        ) {
                          // Split the text at "Date:" to create separate paragraphs
                          const parts = text.split("Date:");

                          // Add company name paragraph
                          docxElements.push(
                            new Paragraph({
                              text: parts[0].trim(),
                              alignment: AlignmentType.CENTER,
                              spacing: { after: 200 },
                            })
                          );

                          // Add date paragraph
                          docxElements.push(
                            new Paragraph({
                              text: "Date:" + parts[1].trim(),
                              alignment: AlignmentType.CENTER,
                              spacing: { after: 200 },
                            })
                          );
                        } else {
                          docxElements.push(
                            new Paragraph({
                              text: text,
                              alignment: AlignmentType.CENTER,
                              spacing: { after: 200 },
                            })
                          );
                        }
                      }
                    }
                  });

                  // Add page break after cover page
                  docxElements.push(
                    new Paragraph({
                      text: "",
                      pageBreakBefore: true,
                    })
                  );
                } else {
                  // Process child elements recursively
                  const childElements = convertHtmlToDocx(el);
                  docxElements.push(...childElements);
                }
                break;

              default:
                // For other elements, process their children recursively
                if (el.childNodes.length > 0) {
                  const childElements = convertHtmlToDocx(el);
                  docxElements.push(...childElements);
                }
                break;
            }
          }
        });

        return docxElements;
      };

      // Process list items with proper indentation and numbering/bullets
      const processListItems = (
        items: Element[],
        docxElements: any[],
        isOrdered: boolean,
        level: number,
        instanceId: string | null
      ) => {
        items.forEach((item, index) => {
          // Get direct text content (excluding nested lists)
          let textContent = "";
          let hasDirectTextOrParagraphs = false;

          // Process direct text and paragraphs
          Array.from(item.childNodes).forEach((child) => {
            if (child.nodeType === Node.TEXT_NODE) {
              textContent += child.textContent?.trim() || "";
              if (child.textContent?.trim()) {
                hasDirectTextOrParagraphs = true;
              }
            } else if (child.nodeType === Node.ELEMENT_NODE) {
              const childEl = child as HTMLElement;
              if (childEl.tagName.toLowerCase() === "p") {
                // Process paragraphs inside list item
                if (childEl.textContent?.trim()) {
                  if (isOrdered) {
                    docxElements.push(
                      new Paragraph({
                        text: childEl.textContent || "",
                        numbering: {
                          reference: instanceId || "default-numbering",
                          level: level,
                          instance: instanceId ? undefined : index,
                        },
                        spacing: { after: 120 },
                      })
                    );
                  } else {
                    docxElements.push(
                      new Paragraph({
                        text: childEl.textContent || "",
                        bullet: { level: level },
                        spacing: { after: 120 },
                      })
                    );
                  }
                  hasDirectTextOrParagraphs = true;
                }
              } else if (
                childEl.tagName.toLowerCase() !== "ul" &&
                childEl.tagName.toLowerCase() !== "ol"
              ) {
                textContent += childEl.textContent?.trim() || "";
                if (childEl.textContent?.trim()) {
                  hasDirectTextOrParagraphs = true;
                }
              }
            }
          });

          // Add the direct text content of the list item if there is any
          if (textContent.trim() && !item.querySelector(":scope > p")) {
            if (isOrdered) {
              docxElements.push(
                new Paragraph({
                  text: textContent.trim(),
                  numbering: {
                    reference: instanceId || "default-numbering",
                    level: level,
                    instance: instanceId ? undefined : index,
                  },
                  spacing: { after: 120 },
                })
              );
            } else {
              docxElements.push(
                new Paragraph({
                  text: textContent.trim(),
                  bullet: { level: level },
                  spacing: { after: 120 },
                })
              );
            }
          }

          // Process nested lists
          const nestedOls = item.querySelectorAll(":scope > ol");
          Array.from(nestedOls).forEach((nestedOl) => {
            // Create a new instance for nested ordered lists
            listInstanceCounter++;
            const nestedInstanceId = instanceId
              ? `${instanceId}-sub-${listInstanceCounter}`
              : `list-${listInstanceCounter}`;

            const nestedItems = nestedOl.querySelectorAll(":scope > li");
            processListItems(
              Array.from(nestedItems),
              docxElements,
              true,
              level + 1,
              nestedInstanceId
            );
          });

          const nestedUls = item.querySelectorAll(":scope > ul");
          Array.from(nestedUls).forEach((nestedUl) => {
            const nestedItems = nestedUl.querySelectorAll(":scope > li");
            processListItems(
              Array.from(nestedItems),
              docxElements,
              false,
              level + 1,
              null
            );
          });

          // If there was no direct text content and no paragraphs but there are nested lists,
          // we need to add an empty list item to maintain proper structure
          if (
            !hasDirectTextOrParagraphs &&
            (item.querySelector(":scope > ol") ||
              item.querySelector(":scope > ul"))
          ) {
            if (isOrdered) {
              docxElements.push(
                new Paragraph({
                  text: "", // Empty text for structure
                  numbering: {
                    reference: instanceId || "default-numbering",
                    level: level,
                    instance: instanceId ? undefined : index,
                  },
                  spacing: { after: 0 },
                })
              );
            } else {
              docxElements.push(
                new Paragraph({
                  text: "", // Empty text for structure
                  bullet: { level: level },
                  spacing: { after: 0 },
                })
              );
            }
          }
        });
      };

      // Process the HTML content
      const { element } = processHtmlContent();

      // Create document sections from HTML content only
      const documentElements = convertHtmlToDocx(element);

      // Create the document with numbered lists support - create a numbering config for each list instance
      const numberingConfigs = [];
      for (let i = 1; i <= listInstanceCounter; i++) {
        numberingConfigs.push({
          reference: `list-${i}`,
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: "%1.",
              alignment: AlignmentType.LEFT,
              style: {
                paragraph: {
                  indent: { left: 720, hanging: 360 },
                },
              },
            },
            {
              level: 1,
              format: LevelFormat.LOWER_LETTER,
              text: "%2.",
              alignment: AlignmentType.LEFT,
              style: {
                paragraph: {
                  indent: { left: 1440, hanging: 360 },
                },
              },
            },
            {
              level: 2,
              format: LevelFormat.LOWER_ROMAN,
              text: "%3.",
              alignment: AlignmentType.LEFT,
              style: {
                paragraph: {
                  indent: { left: 2160, hanging: 360 },
                },
              },
            },
          ],
        });

        // Add any nested list configurations
        for (let j = 1; j <= listInstanceCounter; j++) {
          const nestedRef = `list-${i}-sub-${j}`;
          numberingConfigs.push({
            reference: nestedRef,
            levels: [
              {
                level: 0,
                format: LevelFormat.DECIMAL,
                text: "%1.",
                alignment: AlignmentType.LEFT,
                style: {
                  paragraph: {
                    indent: { left: 720, hanging: 360 },
                  },
                },
              },
              {
                level: 1,
                format: LevelFormat.LOWER_LETTER,
                text: "%2.",
                alignment: AlignmentType.LEFT,
                style: {
                  paragraph: {
                    indent: { left: 1440, hanging: 360 },
                  },
                },
              },
              {
                level: 2,
                format: LevelFormat.LOWER_ROMAN,
                text: "%3.",
                alignment: AlignmentType.LEFT,
                style: {
                  paragraph: {
                    indent: { left: 2160, hanging: 360 },
                  },
                },
              },
            ],
          });
        }
      }

      // Add default numbering for backward compatibility
      numberingConfigs.push({
        reference: "default-numbering",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 720, hanging: 360 },
              },
            },
          },
          {
            level: 1,
            format: LevelFormat.LOWER_LETTER,
            text: "%2.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 1440, hanging: 360 },
              },
            },
          },
          {
            level: 2,
            format: LevelFormat.LOWER_ROMAN,
            text: "%3.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 2160, hanging: 360 },
              },
            },
          },
        ],
      });

      const doc = new Document({
        numbering: {
          config: numberingConfigs,
        },
        sections: [
          {
            properties: {},
            children: documentElements,
          },
        ],
      });

      // Serialize the document
      const buffer = await Packer.toBuffer(doc);

      // Create a Blob and download
      const blob = new Blob([buffer], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const url = URL.createObjectURL(blob);

      // Create download link
      const link = document.createElement("a");
      link.href = url;
      link.download = `${previewFormData.project_title || "RFP_Document"}_${format(new Date(), "yyyy-MM-dd")}.docx`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Clean up
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast({
        title: "DOC Downloaded",
        description:
          "Your RFP document has been downloaded as a Word document.",
      });
    } catch (error) {
      console.error("Error generating DOC:", error);
      toast({
        title: "Error downloading DOC",
        description:
          "There was an error generating your DOC file. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <Button
      onClick={handleDownloadDoc}
      className="gap-1 ml-2"
      variant="outline"
    >
      <FileText className="h-4 w-4" />
      Download DOC
    </Button>
  );
}
