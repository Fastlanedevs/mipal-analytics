import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { format } from "date-fns";

interface PdfDownloaderProps {
  rawHtmlContent: string;
  previewFormData: {
    client_name: string;
    company_name: string;
    date: string;
    project_title: string;
  };
}

export default function PdfDownloader({
  rawHtmlContent,
  previewFormData,
}: PdfDownloaderProps) {
  const handleDownloadPdf = async () => {
    try {
      toast({
        title: "Preparing document",
        description: "Setting up your document for PDF export...",
      });

      // Dynamically import html2pdf.js only when needed
      const html2pdf = (await import("html2pdf.js")).default;

      // Step 1: Create a properly formatted container that matches the A4 preview
      const pdfContainer = document.createElement("div");

      // Clean the HTML content more thoroughly to prevent blank pages
      const processHtmlForPdf = () => {
        try {
          // Process the HTML content to remove elements that might cause blank pages
          let cleanedHtml = rawHtmlContent;

          // Find the first meaningful content element - particularly looking for centered content
          const firstCenteredContentMatch = cleanedHtml.match(
            /<div[^>]*style="[^"]*padding:\s*30mm\s+25mm;\s*display:\s*flex;\s*flex-direction:\s*column;\s*align-items:\s*center;\s*justify-content:\s*center;\s*text-align:\s*center;[^"]*"[^>]*>/
          );

          // If the first element is a centered content element, we need special handling
          if (firstCenteredContentMatch && firstCenteredContentMatch.index) {
            // Get all content before the first centered div
            const beforeCentered = cleanedHtml.substring(
              0,
              firstCenteredContentMatch.index
            );

            // Check if there's only whitespace, comments, or empty elements before
            const isOnlyEmpty =
              /^\s*(?:<\!--.*?-->|<[^>]*>\s*(?:&nbsp;)?\s*<\/[^>]*>)*\s*$/.test(
                beforeCentered
              );

            if (isOnlyEmpty) {
              // If only empty content before the centered div, remove it all
              cleanedHtml = cleanedHtml.substring(
                firstCenteredContentMatch.index
              );

              // Replace the first centered div with a version that doesn't have page break before
              cleanedHtml = cleanedHtml.replace(
                /<div([^>]*style="[^"]*padding:\s*30mm\s+25mm;\s*display:\s*flex;\s*flex-direction:\s*column;\s*align-items:\s*center;\s*justify-content:\s*center;\s*text-align:\s*center;[^"]*")([^>]*)>/,
                '<div$1 data-first-centered="true" style="page-break-before: auto; break-before: auto; margin-top: 0; padding-top: 0;"$2>'
              );
            }
          }

          // Apply various transformations to clean up the HTML for PDF generation
          // Remove any empty elements at the very beginning of the document to prevent blank first page
          cleanedHtml = cleanedHtml.replace(
            /^(\s*<[^>]*>\s*(?:&nbsp;)?\s*<\/[^>]*>\s*)+/,
            ""
          );

          // Process centered content divs
          cleanedHtml = cleanedHtml.replace(
            /(<div[^>]*style="[^"]*padding:\s*30mm\s+25mm;\s*display:\s*flex;\s*flex-direction:\s*column;\s*align-items:\s*center;\s*justify-content:\s*center;\s*text-align:\s*center;[^"]*"[^>]*>)([\s\S]*?)(<\/div>)/g,
            (match, openTag, content, closeTag, offset) => {
              if (
                offset < 100 ||
                openTag.includes('data-first-centered="true"')
              ) {
                return `<div class="custom-center-content first-centered">${content}</div>`;
              }
              return `<div class="custom-center-content">${content}</div>`;
            }
          );

          // Remove divs that might follow centered content and cause blank pages
          cleanedHtml = cleanedHtml.replace(
            /(<div class="custom-center-content">[\s\S]*?<\/div>)(\s*<div[^>]*>\s*(?:&nbsp;)?\s*<\/div>)/g,
            "$1"
          );

          // Clean up empty elements
          cleanedHtml = cleanedHtml.replace(/<p>\s*<\/p>/g, "");
          cleanedHtml = cleanedHtml.replace(/<div>\s*<\/div>/g, "");
          cleanedHtml = cleanedHtml.replace(/<p>\s*&nbsp;\s*<\/p>/g, "");
          cleanedHtml = cleanedHtml.replace(/<div>\s*&nbsp;\s*<\/div>/g, "");

          // Consolidate multiple consecutive page breaks
          cleanedHtml = cleanedHtml.replace(
            /(<div[^>]*page-break[^>]*>[^<]*<\/div>\s*){2,}/gi,
            '<div class="force-page-break">&nbsp;</div>'
          );

          // Remove excessive line breaks
          cleanedHtml = cleanedHtml.replace(
            /(<br\s*\/?>){3,}/g,
            "<br /><br />"
          );

          // Apply specific classes for centered content
          cleanedHtml = cleanedHtml.replace(
            /<div class="custom-center-content( first-centered)?">([\s\S]*?)<\/div>/g,
            (match, firstClass, content) => {
              if (firstClass) {
                return `<div class="center-on-page first-page-center">${content}</div>`;
              }
              return `<div class="center-on-page">${content}</div>`;
            }
          );

          // Handle page breaks
          cleanedHtml = cleanedHtml.replace(
            /<div\s+style="page-break-after:\s*always;">\s*<\/div>/g,
            '<div class="force-page-break">&nbsp;</div>'
          );
          cleanedHtml = cleanedHtml.replace(
            /<div[^>]*style="[^"]*page-break-before[^"]*"[^>]*>/g,
            '<div class="page-break">'
          );
          cleanedHtml = cleanedHtml.replace(
            /<div[^>]*style="[^"]*page-break-after[^"]*"[^>]*>/g,
            '<div class="force-page-break">'
          );

          // Fix first element margins
          cleanedHtml = cleanedHtml.replace(
            /^(<[^>]+>)/,
            "$1<style>.document-container > *:first-child { margin-top: 0 !important; padding-top: 0 !important; }</style>"
          );

          // Add space after last paragraph
          cleanedHtml = cleanedHtml.replace(
            /<\/p>\s*$/,
            '<\/p><div style="height: 5mm;"></div>'
          );

          // Clean up empty elements between page breaks
          cleanedHtml = cleanedHtml.replace(
            /(<div class="(?:force-page-break|page-break)"[^>]*>[^<]*<\/div>)\s*(<div[^>]*>\s*(?:&nbsp;)?\s*<\/div>)\s*(<div class="(?:force-page-break|page-break)"[^>]*>[^<]*<\/div>)/gi,
            "$1$3"
          );

          return cleanedHtml;
        } catch (e) {
          console.error("Error processing HTML for PDF:", e);
          return rawHtmlContent;
        }
      };

      // Create the HTML structure for the PDF with proper styling
      const contentHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman:wght@400;700&display=swap');
          
          body {
            font-family: 'Times New Roman', Times, serif;
            color: black;
            font-size: 12pt;
            line-height: 1.5;
            margin: 0;
            padding: 0;
            overflow: hidden;
          }
          
          * {
            box-sizing: border-box;
            color: black;
            font-family: 'Times New Roman', Times, serif;
          }
          
          h1, h2, h3, h4, h5, h6 {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
            font-weight: bold;
            color: black;
            page-break-after: avoid;
            page-break-inside: avoid;
          }
          
          h1 { font-size: 20pt; }
          h2 { font-size: 16pt; }
          h3 { font-size: 14pt; }
          
          p {
            margin: 0.5em 0;
            color: black;
            page-break-inside: avoid;
          }
          
          ul {
            padding-left: 2em;
            margin: 0.5em 0;
            color: black;
            list-style-position: outside;
            list-style-type: disc;
          }
          
          ol {
            padding-left: 2em;
            margin: 0.5em 0;
            color: black;
            list-style-position: outside;
            list-style-type: decimal;
          }
          
          li {
            margin: 0.25em 0;
            color: black;
            display: list-item;
            line-height: 1.5em;
            position: relative;
            page-break-inside: avoid;
          }
          
          li p {
            margin: 0;
            display: inline;
            page-break-inside: avoid;
          }
          
          ul li {
            list-style-type: disc;
            margin-left: 1em;
          }
          
          ol li {
            list-style-type: decimal;
          }
          
          /* List styling */
          ol.custom-counter {
            counter-reset: item;
            list-style-type: none;
            margin-left: 0;
            padding-left: 2.5em;
          }
          
          ol.custom-counter > li {
            counter-increment: item;
            position: relative;
          }
          
          ol.custom-counter > li::before {
            content: counter(item) ".";
            position: absolute;
            left: -2em;
            width: 1.5em;
            text-align: right;
            color: black;
          }
          
          ul li::before {
            content: "";
            display: none;
          }
          
          table {
            border-collapse: collapse;
            width: 100%;
            margin: 0.5em 0;
            page-break-inside: avoid;
          }
          
          td, th {
            border: 1px solid black;
            padding: 8px;
            color: black;
            text-align: left;
            page-break-inside: avoid;
          }
          
          th {
            background-color: #f0f0f0;
            font-weight: bold;
          }

          img {
            max-width: 100%;
            page-break-inside: avoid;
          }

          .document-container {
            width: 100%;
            padding: 0 0 10mm 0;
            background-color: white;
            overflow: hidden;
          }
          
          .document-container > :last-child {
            page-break-after: avoid;
            margin-bottom: 5mm;
            padding-bottom: 5mm;
          }
          
          .document-container > :first-child {
            margin-top: 0;
            padding-top: 0;
          }
          
          .document-container br:last-child,
          .document-container p:empty,
          .document-container div:empty {
            display: none;
          }
          
          .page-break {
            display: block;
            clear: both;
            page-break-before: always;
            page-break-after: avoid;
            height: 0;
            margin: 0;
            padding: 0;
          }
          
          .force-page-break {
            display: block;
            height: 0;
            page-break-after: always;
            break-after: page;
            visibility: hidden;
            margin: 0;
            padding: 0;
          }
          
          .center-on-page {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            min-height: auto !important;
            padding: 30mm 25mm !important;
            page-break-before: always !important;
            page-break-after: avoid !important;
            break-after: avoid !important;
            break-before: page !important;
            margin-bottom: 0 !important;
          }
          
          .center-on-page::after {
            display: none;
          }

          .document-container > *:first-child:not(.center-on-page) {
            page-break-before: avoid !important;
            break-before: avoid !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
          }

          .first-page-center {
            page-break-before: auto !important;
            break-before: auto !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
          }
        </style>
      </head>
      <body>
        <div class="document-container">
          ${processHtmlForPdf()}
        </div>
      </body>
      </html>
    `;

      pdfContainer.innerHTML = contentHtml;

      // Style the container for PDF rendering
      pdfContainer.style.width = "210mm";
      pdfContainer.style.minHeight = "297mm";
      pdfContainer.style.position = "absolute";
      pdfContainer.style.left = "-9999px";
      pdfContainer.style.top = "0";
      pdfContainer.style.overflow = "hidden";
      pdfContainer.style.pageBreakAfter = "avoid";

      // Add to document body for rendering
      document.body.appendChild(pdfContainer);

      // Find the document container
      const pdfDocumentContainer = pdfContainer.querySelector(
        ".document-container"
      );
      if (!pdfDocumentContainer) {
        throw new Error("Could not find document container element");
      }

      // Add style overrides
      const styleOverride = document.createElement("style");
      styleOverride.textContent = `
        .document-container > *:first-child {
          page-break-before: auto !important;
          break-before: auto !important;
          margin-top: 0 !important;
          padding-top: 0 !important;
        }
        .center-on-page.first-page-center {
          page-break-before: auto !important;
          break-before: auto !important;
        }
        .center-on-page {
          page-break-after: avoid !important;
          break-after: avoid !important;
        }
        .center-on-page + * {
          page-break-before: avoid !important;
          break-before: avoid !important;
        }
      `;
      pdfContainer.insertBefore(styleOverride, pdfContainer.firstChild);

      // Remove empty elements at the beginning
      const childNodes = pdfDocumentContainer.childNodes;
      let startIndex = 0;
      for (let i = 0; i < childNodes.length; i++) {
        const node = childNodes[i];
        if (node.nodeType === 1) {
          // Element node
          const element = node as Element;
          if (
            element.textContent?.trim() === "" ||
            element.innerHTML.trim() === "&nbsp;" ||
            (element.innerHTML.trim().length < 5 &&
              !element.className.includes("center-on-page"))
          ) {
            startIndex = i + 1;
          } else {
            break;
          }
        } else if (node.nodeType === 3) {
          // Text node
          if (node.textContent?.trim() === "") {
            startIndex = i + 1;
          } else {
            break;
          }
        }
      }

      // Remove the empty elements
      for (let i = 0; i < startIndex; i++) {
        if (pdfDocumentContainer.firstChild) {
          pdfDocumentContainer.removeChild(pdfDocumentContainer.firstChild);
        }
      }

      // Fix first element styling
      const firstElement = pdfDocumentContainer.firstElementChild;
      if (firstElement && firstElement.className.includes("center-on-page")) {
        (firstElement as HTMLElement).style.pageBreakBefore = "avoid";
        (firstElement as HTMLElement).style.breakBefore = "avoid";
      }

      toast({
        title: "Generating PDF",
        description: "Converting document to PDF format...",
      });

      // Configure options for html2pdf
      const opt = {
        margin: [25.4, 25.4, 30, 25.4],
        filename: `${previewFormData.project_title || "RFP_Document"}_${format(new Date(), "yyyy-MM-dd")}.pdf`,
        image: { type: "jpeg", quality: 1 },
        enableLinks: true,
        html2canvas: {
          scale: 2,
          useCORS: true,
          letterRendering: true,
          allowTaint: true,
          logging: false,
          backgroundColor: "#FFFFFF",
          windowHeight: window.innerHeight,
          removeContainer: true,
        },
        jsPDF: {
          unit: "mm",
          format: "a4",
          orientation: "portrait",
          compress: true,
          hotfixes: ["px_scaling"],
          putTotalPages: false,
        },
        pagebreak: {
          mode: ["avoid-all", "css", "legacy"],
          before: ".page-break",
          after: [".force-page-break"],
          avoid: [
            "img",
            "table",
            "tr",
            "td",
            "li",
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "[data-pdf-no-blank]",
          ],
        },
      };

      // Apply formatting fixes to list items
      const fixListItemAlignment = (container: Element) => {
        // Process list items
        const listItems = container.querySelectorAll("li");
        listItems.forEach((li) => {
          const isOrderedList =
            li.parentElement?.tagName.toLowerCase() === "ol";
          if (isOrderedList) {
            li.style.position = "relative";
            li.style.pageBreakInside = "avoid";
            li.style.display = "flex";
            const content = li.innerHTML;
            li.innerHTML = `<span style="display: block; flex: 1;">${content}</span>`;
          } else {
            li.style.position = "relative";
            li.style.pageBreakInside = "avoid";
            li.style.listStyleType = "none";
            li.style.display = "table";
            li.style.width = "100%";
            const content = li.innerHTML;
            li.innerHTML = `
              <div style="display: table-row;">
                <div style="display: table-cell; width: 1em; padding-right: 0.5em; vertical-align: top;">•</div>
                <div style="display: table-cell; vertical-align: top;">${content}</div>
              </div>
            `;
          }
        });

        // Fix ordered lists
        const olLists = container.querySelectorAll("ol");
        olLists.forEach((ol) => {
          ol.classList.add("custom-counter");
          ol.setAttribute("start", "1");
        });

        // Fix unordered lists
        const ulLists = container.querySelectorAll("ul");
        ulLists.forEach((ul) => {
          ul.style.listStyleType = "none";
          ul.style.paddingLeft = "1em";
          ul.style.marginLeft = "0";
        });

        // Add page break control
        const paragraphs = container.querySelectorAll("p");
        paragraphs.forEach((p) => {
          p.setAttribute("style", "page-break-inside: avoid;");
        });

        const headings = container.querySelectorAll("h1, h2, h3, h4, h5, h6");
        headings.forEach((h) => {
          h.setAttribute(
            "style",
            "page-break-inside: avoid; page-break-after: avoid;"
          );
        });

        // Remove empty elements
        const allElements = container.querySelectorAll("*");
        allElements.forEach((el) => {
          if (
            el.innerHTML.trim() === "" &&
            !["br", "hr", "img"].includes(el.tagName.toLowerCase()) &&
            el.childNodes.length === 0
          ) {
            el.remove();
          }
        });

        // Fix page breaks
        const pageBreaks = container.querySelectorAll(
          'div[style*="page-break-before"], div[style*="page-break-after"]'
        );
        pageBreaks.forEach((pb) => {
          pb.className = "page-break";
          if (pb.innerHTML.trim() === "") {
            pb.innerHTML = "&nbsp;";
          }
        });
      };

      // Apply explicit page breaks
      const applyExplicitPageBreaks = (container: Element) => {
        // Process page break divs
        const pageBreakDivs = container.querySelectorAll(
          'div[style*="page-break-after: always"]'
        );
        pageBreakDivs.forEach((div) => {
          div.className = "force-page-break";
          div.innerHTML = "&nbsp;";
          (div as HTMLElement).style.height = "0";
          (div as HTMLElement).style.margin = "0";
          (div as HTMLElement).style.padding = "0";
        });

        // Handle centered content
        const centeredDivs = container.querySelectorAll(
          'div[style*="padding: 30mm 25mm"][style*="display: flex"][style*="flex-direction: column"][style*="align-items: center"][style*="justify-content: center"][style*="text-align: center"]'
        );

        centeredDivs.forEach((div, index) => {
          if (index === 0 && !div.previousElementSibling) {
            div.className = "center-on-page first-page-center";
            (div as HTMLElement).style.pageBreakBefore = "auto";
            (div as HTMLElement).style.breakBefore = "auto";
          } else {
            div.className = "center-on-page";
            (div as HTMLElement).style.pageBreakBefore = "always";
            (div as HTMLElement).style.breakBefore = "page";
          }

          (div as HTMLElement).style.pageBreakAfter = "avoid";
          (div as HTMLElement).style.breakAfter = "avoid";
          (div as HTMLElement).style.marginBottom = "0";
          (div as HTMLElement).setAttribute("data-pdf-no-blank", "true");

          // Clean up blank divs around centered content
          const prevSibling = div.previousElementSibling;
          if (
            prevSibling &&
            (prevSibling.textContent?.trim() === "" ||
              prevSibling.innerHTML.trim() === "&nbsp;" ||
              prevSibling.className.includes("page-break"))
          ) {
            prevSibling.remove();
          }

          // Remove empty elements after centered content
          let nextSibling = div.nextElementSibling;
          for (let i = 0; i < 3; i++) {
            if (
              nextSibling &&
              (!nextSibling.textContent ||
                nextSibling.textContent.trim() === "" ||
                nextSibling.innerHTML.trim() === "&nbsp;" ||
                nextSibling.innerHTML.trim().length < 5 ||
                nextSibling.className.includes("page-break"))
            ) {
              const tmpNext = nextSibling.nextElementSibling;
              nextSibling.remove();
              nextSibling = tmpNext;
            } else {
              break;
            }
          }

          // Add non-breaking element
          const nonBreakingEl = document.createElement("div");
          nonBreakingEl.style.pageBreakBefore = "avoid";
          nonBreakingEl.style.pageBreakAfter = "avoid";
          nonBreakingEl.style.breakBefore = "avoid";
          nonBreakingEl.style.breakAfter = "avoid";
          nonBreakingEl.style.height = "1px";
          nonBreakingEl.style.margin = "0";
          nonBreakingEl.style.padding = "0";
          nonBreakingEl.style.visibility = "hidden";
          nonBreakingEl.innerHTML = "&nbsp;";

          if (nextSibling) {
            div.parentNode?.insertBefore(nonBreakingEl, nextSibling);
          } else if (div.parentNode) {
            div.parentNode.appendChild(nonBreakingEl);
          }
        });

        // Remove consecutive page breaks
        const allPageBreaks = Array.from(
          container.querySelectorAll(".force-page-break, .page-break")
        );
        for (let i = 0; i < allPageBreaks.length - 1; i++) {
          const currentBreak = allPageBreaks[i];
          const nextBreak = allPageBreaks[i + 1];
          const nextElement = currentBreak.nextElementSibling;

          if (
            nextElement === nextBreak ||
            (nextElement &&
              nextElement.textContent &&
              nextElement.textContent.trim() === "" &&
              nextElement.nextElementSibling === nextBreak)
          ) {
            nextBreak.remove();
          }
        }

        // Fix content after page breaks
        allPageBreaks.forEach((breakEl) => {
          const nextEl = breakEl.nextElementSibling;
          if (
            nextEl &&
            ((nextEl.textContent && nextEl.textContent.trim() === "") ||
              nextEl.innerHTML.trim() === "&nbsp;")
          ) {
            nextEl.remove();
          }
        });
      };

      // Apply list and page break fixes
      fixListItemAlignment(pdfDocumentContainer);
      applyExplicitPageBreaks(pdfDocumentContainer);

      // Generate the PDF
      html2pdf()
        .from(pdfDocumentContainer as HTMLElement)
        .set(opt)
        .save()
        .then(() => {
          // Clean up
          document.body.removeChild(pdfContainer);

          toast({
            title: "PDF Downloaded",
            description: "Your RFP document has been downloaded successfully.",
          });
        })
        .catch((error: Error) => {
          console.error("PDF generation error:", error);
          document.body.removeChild(pdfContainer);

          toast({
            title: "Error downloading PDF",
            description:
              "There was an error generating your PDF. Please try again.",
            variant: "destructive",
          });
        });
    } catch (error) {
      console.error("Exception in PDF generation:", error);
      toast({
        title: "Error downloading PDF",
        description: "There was an unexpected error. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <Button onClick={handleDownloadPdf} className="gap-1">
      <Download className="h-4 w-4" />
      Download PDF
    </Button>
  );
}
