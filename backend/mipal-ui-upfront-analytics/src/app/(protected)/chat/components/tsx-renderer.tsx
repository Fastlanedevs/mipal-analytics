import React, { useEffect, useRef } from "react";
import * as ReactDOMServer from "react-dom/server";
import { transform } from "@babel/standalone";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableCell,
  TableHead,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertCircle,
  Leaf,
  Users,
  Factory,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

interface TsxRendererProps {
  code: string;
}

const TsxRenderer: React.FC<TsxRendererProps> = ({ code }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const renderComponent = () => {
      try {
        // Remove import statements and export default
        const cleanedCode = code
          .replace(/import\s+.*?from\s+['"].*?['"];?/g, "")
          .replace(/export\s+default\s+/g, "")
          .replace(/'use client'/, ""); // Remove 'use client' directive

        // Transform TypeScript to JavaScript
        const transformedTs = transform(cleanedCode, {
          presets: ["typescript", "react"],
          filename: "dynamic.tsx",
        }).code;

        // Wrap the transformed code in an IIFE
        const wrappedCode = `
          (function(React, Avatar, AvatarFallback, AvatarImage, Card, CardContent, 
          CardHeader, CardTitle, Button, Input, Table, TableHeader, TableBody, TableRow, 
          TableCell, TableHead, AlertCircle, Leaf, Users, Factory, TrendingDown, TrendingUp) {
            ${transformedTs}
            return typeof Page === 'function' ? React.createElement(Page) :
                   typeof FinanceAdvisoryCompetitiveAnalysis === 'function' ? React.createElement(FinanceAdvisoryCompetitiveAnalysis) :
                   typeof SalesPitchPlan === 'function' ? React.createElement(SalesPitchPlan) :
                   null;
          })
        `;

        // Transform the wrapped code
        const transformedCode = transform(wrappedCode, {
          presets: ["react"],
          filename: "dynamic.js",
        }).code;

        if (typeof transformedCode !== "string") {
          throw new Error("Transformed code is not a string");
        }

        // Render the component to an HTML string
        const componentFunction = eval(transformedCode);
        const element = componentFunction(
          React,
          Avatar,
          AvatarFallback,
          AvatarImage,
          Card,
          CardContent,
          CardHeader,
          CardTitle,
          Button,
          Input,
          Table,
          TableHeader,
          TableBody,
          TableRow,
          TableCell,
          TableHead,
          AlertCircle,
          Leaf,
          Users,
          Factory,
          TrendingDown,
          TrendingUp
        );
        const htmlString = ReactDOMServer.renderToString(element);

        // Update the iframe content
        if (iframeRef.current) {
          const iframeDoc = iframeRef.current.contentDocument;
          if (iframeDoc) {
            iframeDoc.open();
            iframeDoc.write(`
              <!DOCTYPE html>
              <html>
                <head>
                  <meta charset="UTF-8" />
                  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                  <script src="https://cdn.tailwindcss.com"></script>
                  <style>
                    /* Add styles for components */
                    .card {
                      background: white;
                      border-radius: 0.5rem;
                      box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                    }
                    .bg-gray-50 { background-color: #F9FAFB; }
                    .bg-gray-100 { background-color: #F3F4F6; }
                    .text-green-600 { color: #059669; }
                    .text-red-600 { color: #DC2626; }
                  </style>
                </head>
                <body>
                  <div id="root">${htmlString}</div>
                  <script src="https://unpkg.com/react@17/umd/react.development.js"></script>
                  <script src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
                  <script>
                    const componentFunction = ${transformedCode};
                    const element = componentFunction(
                      React,
                      ${Avatar.toString()},
                      ${AvatarFallback.toString()},
                      ${AvatarImage.toString()},
                      ${Card.toString()},
                      ${CardContent.toString()},
                      ${CardHeader.toString()},
                      ${CardTitle.toString()},
                      ${Button.toString()},
                      ${Input.toString()},
                      ${Table.toString()},
                      ${TableHeader.toString()},
                      ${TableBody.toString()},
                      ${TableRow.toString()},
                      ${TableCell.toString()},
                      ${TableHead.toString()},
                      ${AlertCircle.toString()},
                      ${Leaf.toString()},
                      ${Users.toString()},
                      ${Factory.toString()},
                      ${TrendingDown.toString()},
                      ${TrendingUp.toString()}
                    );
                    ReactDOM.hydrate(element, document.getElementById('root'));
                  </script>
                </body>
              </html>
            `);
            iframeDoc.close();
          }
        }
      } catch (error) {
        console.error("Error rendering TSX:", error);
        if (iframeRef.current) {
          const iframeDoc = iframeRef.current.contentDocument;
          if (iframeDoc) {
            iframeDoc.open();
            iframeDoc.write(`
              <div style="color: red; padding: 20px;">
                <h2>Error rendering TSX:</h2>
                <pre>${error instanceof Error ? error.message : String(error)}</pre>
              </div>
            `);
            iframeDoc.close();
          }
        }
      }
    };

    renderComponent();
  }, [code]);

  return (
    <iframe
      ref={iframeRef}
      style={{ width: "100%", height: "85vh", border: "none" }}
      title="Dynamic TSX Renderer"
    />
  );
};

export default TsxRenderer;
