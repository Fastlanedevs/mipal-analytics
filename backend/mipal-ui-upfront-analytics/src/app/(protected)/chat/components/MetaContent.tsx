import { motion } from "framer-motion";
import { LocalThinkingDescription } from "./MessageItem";
import { useState } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@radix-ui/react-icons";
import { cn } from "@/lib/utils";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export default function MetaContent({
  step,
  stepIndex,
  showTyping,
  showCompleted,
}: {
  step: any;
  stepIndex: number;
  showTyping: boolean;
  showCompleted: boolean;
}) {
  const hasDescription = step.description && step.description.length > 0;

  // If showCompleted is true (when not streaming), the accordion is closed
  const [isOpen, setIsOpen] = useState(() => (showCompleted ? false : true));

  const toggleAccordion = () => {
    if (hasDescription) {
      setIsOpen(!isOpen);
    }
  };

  return (
    <motion.div
      key={step.id || stepIndex}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: stepIndex * 0.1 }}
      className="space-y-3"
    >
      <div
        onClick={toggleAccordion}
        className={cn(
          "justify-between flex items-center",
          hasDescription && "cursor-pointer"
        )}
      >
        <div className="flex items-center space-x-2 w-full">
          <motion.div
            className="h-5 w-5 flex items-center justify-center text-primary"
            // animate={{
            //   scale: step.status === "inprogress" ? [1, 1.1, 1] : 1,
            //   opacity: step.status === "inprogress" ? [0.7, 1, 0.7] : 1,
            // }}
            transition={{
              repeat: Infinity,
              duration: 1.5,
            }}
          >
            {step.status === "completed" ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6L9 17l-5-5" />
              </svg>
            ) : step.status === "error" ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-red-500"
              >
                <circle cx="10" cy="10" r="8" />
                <line x1="10" y1="6" x2="10" y2="10" />
                <line x1="10" y1="14" x2="10" y2="14" />
              </svg>
            ) : (
              // <span className="w-2 h-2 rounded-full bg-foreground/50"></span>
              <LoadingSpinner size={12} />
            )}
          </motion.div>
          <motion.span
            className={`font-medium text-sm ${
              step.status === "inprogress"
                ? "text-primary"
                : step.status === "completed"
                  ? "text-foreground"
                  : step.status === "error"
                    ? "text-red-500"
                    : "text-muted-foreground"
            }`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 + stepIndex * 0.1 }}
          >
            {step.title}
          </motion.span>
        </div>

        {hasDescription &&
          (isOpen ? (
            <ChevronUpIcon className="w-4 h-4" />
          ) : (
            <ChevronDownIcon className="w-4 h-4" />
          ))}
      </div>

      {isOpen && hasDescription && step.status !== "pending" && (
        <div className="ml-7 pl-4 border-l-2 border-primary/30 space-y-2">
          {step.description.map
            ? step.description.map(
                (desc: LocalThinkingDescription, idx: number) => (
                  <motion.div
                    key={idx}
                    className="space-y-1"
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + idx * 0.1 }}
                  >
                    <div className="text-xs font-medium text-foreground/90 flex items-center gap-2">
                      <motion.div
                        className="h-1.5 w-1.5 rounded-full bg-primary/50"
                        animate={{
                          scale: desc.status === "inprogress" ? [1, 1.5, 1] : 1,
                        }}
                        transition={{
                          repeat: Infinity,
                          duration: 2,
                        }}
                      />
                      {desc.title}
                    </div>

                    {desc.execution && (
                      <motion.div
                        className={`bg-gray-50 dark:bg-[hsl(var(--subtle-bg))]/50 rounded-md p-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap shadow-sm border ${
                          desc.status === "error"
                            ? "border-red-500/20 bg-red-50 dark:bg-red-950/20"
                            : "border-muted-foreground/5"
                        }`}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{
                          height: "auto",
                          opacity: 1,
                        }}
                        transition={{ delay: 0.3 + idx * 0.1 }}
                      >
                        {showTyping ? (
                          <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{
                              duration: 0.1,
                              delay: idx * 0.1,
                            }}
                            className={
                              desc.status === "error" ? "text-red-500" : ""
                            }
                          >
                            {desc.execution}
                          </motion.span>
                        ) : (
                          <span className="inline-block h-4 w-3 bg-foreground/70 animate-pulse"></span>
                        )}
                      </motion.div>
                    )}

                    {desc.description && (
                      <motion.div
                        className={`bg-gray-50 dark:bg-[hsl(var(--subtle-bg))]/50 rounded-md p-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap shadow-sm border ${
                          desc.status === "error"
                            ? "border-red-500/20 bg-red-50 dark:bg-red-950/20"
                            : "border-muted-foreground/5"
                        }`}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{
                          height: "auto",
                          opacity: 1,
                        }}
                        transition={{ delay: 0.3 + idx * 0.1 }}
                      >
                        <motion.span
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{
                            duration: 0.1,
                            delay: idx * 0.1,
                          }}
                          className={
                            desc.status === "error" ? "text-red-500" : ""
                          }
                        >
                          {desc.description}
                        </motion.span>
                      </motion.div>
                    )}

                    <div className="flex items-center text-xs justify-between">
                      <div className="flex items-center">
                        <motion.span
                          className={`inline-block h-2 w-2 rounded-full mr-2 ${
                            desc.status === "completed"
                              ? "bg-green-500"
                              : desc.status === "inprogress"
                                ? "bg-primary"
                                : desc.status === "error"
                                  ? "bg-red-500"
                                  : "bg-gray-300"
                          }`}
                          animate={
                            desc.status === "inprogress"
                              ? {
                                  scale: [1, 1.5, 1],
                                  opacity: [0.7, 1, 0.7],
                                }
                              : {}
                          }
                          transition={{
                            repeat: Infinity,
                            duration: 1.2,
                          }}
                        />
                        <span
                          className={`text-muted-foreground capitalize ${
                            desc.status === "error" ? "text-red-500" : ""
                          }`}
                        >
                          {desc.status}
                        </span>
                      </div>

                      {desc.status === "inprogress" && (
                        <span className="text-xs text-muted-foreground/50 flex items-center gap-1">
                          <span className="h-1 w-1 bg-primary rounded-full animate-ping"></span>
                          <span
                            className="h-1 w-1 bg-primary rounded-full animate-ping"
                            style={{ animationDelay: "0.2s" }}
                          ></span>
                          <span
                            className="h-1 w-1 bg-primary rounded-full animate-ping"
                            style={{ animationDelay: "0.4s" }}
                          ></span>
                        </span>
                      )}
                    </div>

                    {desc.nestedDescriptions &&
                      desc.nestedDescriptions.length > 0 && (
                        <div className="ml-4 mt-2 space-y-2 border-l-2 border-primary/30 pl-4">
                          {desc.nestedDescriptions.map(
                            (nestedDesc: any, nestedIdx: number) => (
                              <motion.div
                                key={nestedIdx}
                                className="space-y-1"
                                initial={{ opacity: 0, x: -5 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.2 + nestedIdx * 0.1 }}
                              >
                                <div className="text-xs font-medium text-foreground/90 flex items-center gap-2">
                                  <motion.div
                                    className="h-1.5 w-1.5 rounded-full bg-primary/50"
                                    animate={{
                                      scale:
                                        nestedDesc.status === "inprogress"
                                          ? [1, 1.5, 1]
                                          : 1,
                                    }}
                                    transition={{
                                      repeat: Infinity,
                                      duration: 2,
                                    }}
                                  />
                                  {nestedDesc.title}
                                </div>

                                {nestedDesc.description && (
                                  <motion.div
                                    className={`bg-gray-50 dark:bg-[hsl(var(--subtle-bg))]/50 rounded-md p-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap shadow-sm border ${
                                      nestedDesc.status === "error"
                                        ? "border-red-500/20 bg-red-50 dark:bg-red-950/20"
                                        : "border-muted-foreground/5"
                                    }`}
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{
                                      height: "auto",
                                      opacity: 1,
                                    }}
                                    transition={{
                                      delay: 0.3 + nestedIdx * 0.1,
                                    }}
                                  >
                                    <motion.span
                                      initial={{ opacity: 0 }}
                                      animate={{ opacity: 1 }}
                                      transition={{
                                        duration: 0.1,
                                        delay: nestedIdx * 0.1,
                                      }}
                                      className={
                                        nestedDesc.status === "error"
                                          ? "text-red-500"
                                          : ""
                                      }
                                    >
                                      {nestedDesc.description}
                                    </motion.span>
                                  </motion.div>
                                )}

                                <div className="flex items-center text-xs justify-between">
                                  <div className="flex items-center">
                                    <motion.span
                                      className={`inline-block h-2 w-2 rounded-full mr-2 ${
                                        nestedDesc.status === "completed"
                                          ? "bg-green-500"
                                          : nestedDesc.status === "inprogress"
                                            ? "bg-primary"
                                            : nestedDesc.status === "error"
                                              ? "bg-red-500"
                                              : "bg-gray-300"
                                      }`}
                                      animate={
                                        nestedDesc.status === "inprogress"
                                          ? {
                                              scale: [1, 1.5, 1],
                                              opacity: [0.7, 1, 0.7],
                                            }
                                          : {}
                                      }
                                      transition={{
                                        repeat: Infinity,
                                        duration: 1.2,
                                      }}
                                    />
                                    <span
                                      className={`text-muted-foreground capitalize ${
                                        nestedDesc.status === "error"
                                          ? "text-red-500"
                                          : ""
                                      }`}
                                    >
                                      {nestedDesc.status}
                                    </span>
                                  </div>

                                  {nestedDesc.status === "inprogress" && (
                                    <span className="text-xs text-muted-foreground/50 flex items-center gap-1">
                                      <span className="h-1 w-1 bg-primary rounded-full animate-ping"></span>
                                      <span
                                        className="h-1 w-1 bg-primary rounded-full animate-ping"
                                        style={{ animationDelay: "0.2s" }}
                                      ></span>
                                      <span
                                        className="h-1 w-1 bg-primary rounded-full animate-ping"
                                        style={{ animationDelay: "0.4s" }}
                                      ></span>
                                    </span>
                                  )}
                                </div>
                              </motion.div>
                            )
                          )}
                        </div>
                      )}
                  </motion.div>
                )
              )
            : null}
        </div>
      )}
    </motion.div>
  );
}
