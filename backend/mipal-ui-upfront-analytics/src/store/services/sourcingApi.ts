import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery, formDataBaseQuery } from "./baseQuery";

interface Category {
  id: string;
  name: string;
  description: string;
}

interface Section {
  heading: string;
  subheading: string;
  content: string | null;
}

interface Template {
  id: string;
  template_id: string;
  industry: string;
  name: string;
  description: string;
  sections: Section[];
  created_at: string;
  updated_at: string;
}

interface TemplateDetailsResponse {
  status: string;
  template_id: string;
  name: string;
  sections: {
    heading: string;
    section_id: string;
    subsections: {
      subheading: string;
      subsection_id: string;
      questions: {
        question_id: string;
        question_name: string;
        is_accepted: boolean;
        answer?: string;
      }[];
    }[];
  }[];
  created_at: string;
  updated_at: string;
  template_status: string;
}

interface SubsectionQuestionsResponse {
  status: string;
  message: string | null;
  template_id: string;
  section_id: string;
  subsection_id: string;
  subheading: string;
  questions: {
    question_id: string;
    question_name: string;
    is_accepted: boolean;
  }[];
}

interface AllTemplatesResponse {
  [industry: string]: Template[];
}

interface Question {
  question_id: string;
  question_name: string;
  is_accepted: boolean;
  answer?: string;
}

interface Answer {
  answer: string;
  question: string;
  question_id: string;
  sources: {
    chunk_id: string;
    file_id: string;
    file_name: string;
    score: number;
  }[];
}

interface SimpleAnswer {
  question_id: string;
  answer: string;
  accept_answer: boolean;
  is_speculative?: boolean;
  sources?: any[];
}

// Create a separate API instance for form data requests
export const formDataApi = createApi({
  reducerPath: "formDataApi",
  baseQuery: formDataBaseQuery,
  tagTypes: ["Template"],
  endpoints: (builder) => ({
    uploadDocument: builder.mutation<
      any,
      {
        templateId: string;
        sectionId: string;
        questionId?: string | null;
        file: File;
      }
    >({
      query: ({ templateId, sectionId, questionId, file }) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("template_id", templateId);
        formData.append("section_id", sectionId);

        if (questionId) {
          formData.append("question_id", questionId);
        }

        return {
          url: "/sourcing/rfp/upload-document",
          method: "POST",
          body: formData,
        };
      },
      invalidatesTags: (result, error, { templateId }) => [
        { type: "Template" as const, id: templateId },
      ],
    }),
    uploadTemplate: builder.mutation<any, File>({
      query: (file) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("name", "");

        return {
          url: "/sourcing/rfp/upload-template",
          method: "POST",
          body: formData,
        };
      },
    }),
  }),
});

// Define a service using a base URL and expected endpoints
export const sourcingApi = createApi({
  reducerPath: "sourcingApi",
  baseQuery: baseQuery,
  tagTypes: ["Template", "SubsectionQuestions", "Answers"],
  endpoints: (builder) => ({
    getSourcingCategories: builder.query<Category[], void>({
      query: () => ({
        url: "/sourcing/categories",
        method: "GET",
        headers: {
          accept: "application/json",
        },
      }),
    }),
    getAllRfpTemplates: builder.query<AllTemplatesResponse, void>({
      query: () => ({
        url: "/sourcing/rfp/all-templates",
        method: "GET",
        headers: {
          accept: "application/json",
        },
      }),
    }),
    downloadTemplate: builder.mutation<Blob, string>({
      query: (format) => ({
        url: `/sourcing/rfp/download-sample-template?format=${format}`,
        method: "GET",
        responseHandler: (response) => response.blob(),
        headers: {
          Accept: "*/*",
        },
      }),
    }),
    updateTemplateName: builder.mutation<
      any,
      { templateId: string; name: string }
    >({
      query: ({ templateId, name }) => ({
        url: `/sourcing/rfp/templates/${templateId}/name`,
        method: "PUT",
        body: { name },
        headers: {
          accept: "application/json",
        },
      }),
    }),
    getTemplateById: builder.query<TemplateDetailsResponse, string>({
      query: (templateId) => ({
        url: `/sourcing/rfp/templates/${templateId}`,
        method: "GET",
        headers: {
          accept: "application/json",
        },
      }),
      providesTags: (result, error, templateId) => [
        { type: "Template" as const, id: templateId },
      ],
    }),
    // get all templates
    getAllTemplates: builder.query<Template[], void>({
      query: () => ({
        url: "/sourcing/rfp/templates",
        method: "GET",
      }),
    }),
    generateSubsectionQuestions: builder.mutation<
      any,
      { templateId: string; subsectionId: string }
    >({
      query: ({ subsectionId }) => ({
        url: `/sourcing/rfp/subsections/${subsectionId}/questions`,
        method: "POST",
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { templateId, subsectionId }) => [
        { type: "SubsectionQuestions" as const, id: subsectionId },
        { type: "Template" as const, id: templateId },
      ],
    }),
    getExistingSubsectionQuestions: builder.query<
      SubsectionQuestionsResponse,
      string
    >({
      query: (subsectionId) => ({
        url: `/sourcing/rfp/subsections/${subsectionId}/questions`,
        method: "GET",
        headers: {
          accept: "application/json",
        },
      }),
      providesTags: (result, error, subsectionId) => [
        { type: "SubsectionQuestions", id: subsectionId },
      ],
    }),
    getPromptQuestions: builder.mutation<
      any,
      { subsectionId: string; prompt: string }
    >({
      query: ({ subsectionId, prompt }) => ({
        url: `/sourcing/rfp/subsections/${subsectionId}/prompt-questions`,
        method: "POST",
        body: { prompt },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { subsectionId }) => [
        { type: "SubsectionQuestions" as const, id: subsectionId },
      ],
    }),
    acceptQuestions: builder.mutation<
      any,
      { templateId: string; subsectionId: string; questionIds: string[] }
    >({
      query: ({ templateId, subsectionId, questionIds }) => ({
        url: `/sourcing/rfp/subsections/${subsectionId}/accept-questions`,
        method: "POST",
        body: {
          template_id: templateId,
          subsection_id: subsectionId,
          question_ids: questionIds,
        },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { templateId, subsectionId }) => [
        { type: "Template" as const, id: templateId },
        { type: "SubsectionQuestions" as const, id: subsectionId },
      ],
    }),
    deleteQuestions: builder.mutation<
      any,
      { templateId: string; subsectionId: string; questionIds: string[] }
    >({
      query: ({ templateId, subsectionId, questionIds }) => ({
        url: `/sourcing/rfp/subsections/${subsectionId}/questions`,
        method: "DELETE",
        body: {
          template_id: templateId,
          subsection_id: subsectionId,
          question_ids: questionIds,
        },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { templateId, subsectionId }) => [
        { type: "Template" as const, id: templateId },
        { type: "SubsectionQuestions" as const, id: subsectionId },
      ],
    }),
    toggleKnowledgePal: builder.mutation<
      any,
      { sectionId: string; enabled: boolean }
    >({
      query: ({ sectionId, enabled }) => ({
        url: `/sourcing/rfp/sections/${sectionId}/toggle-knowledge-pal`,
        method: "POST",
        body: {
          section_id: sectionId,
          enabled: enabled,
        },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { sectionId }) => [
        { type: "Template" as const, id: "LIST" },
      ],
    }),
    deleteDocument: builder.mutation<any, { fileId: string }>({
      query: ({ fileId }) => ({
        url: `/sourcing/rfp/files/${fileId}`,
        method: "DELETE",
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { fileId }) => [
        { type: "Template" as const, id: fileId },
      ],
    }),
    generateSectionAnswers: builder.mutation<
      Answer[],
      { sectionId: string; templateId: string }
    >({
      query: ({ sectionId, templateId }) => ({
        url: `/sourcing/rfp/sections/${sectionId}/templates/${templateId}/answer`,
        method: "POST",
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { sectionId }) => [
        { type: "Answers" as const, id: sectionId },
        { type: "Template" as const, id: "LIST" },
      ],
    }),
    getSectionAnswers: builder.query<Answer[], string>({
      query: (sectionId) => ({
        url: `/sourcing/rfp/sections/${sectionId}/answers`,
        method: "GET",
        headers: {
          accept: "application/json",
        },
      }),
      providesTags: (result, error, sectionId) => [
        { type: "Answers" as const, id: sectionId },
      ],
    }),
    // /sourcing/rfp/templates/{template_id}/save-answers
    saveAnswers: builder.mutation<
      any,
      {
        templateId: string;
        question_id?: string;
        answer?: string;
        accept_answer?: boolean;
        is_speculative?: boolean;
        sources?: any[];
        answers?: Array<{
          question_id: string;
          answer: string;
          accept_answer: boolean;
          is_speculative?: boolean;
          sources?: any[];
        }>;
      }
    >({
      query: ({
        templateId,
        question_id,
        answer,
        accept_answer,
        is_speculative,
        sources,
        answers,
      }) => ({
        url: `/sourcing/rfp/templates/${templateId}/save-answers`,
        method: "POST",
        body: answers
          ? { answers }
          : { question_id, answer, accept_answer, is_speculative, sources },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { templateId }) => [
        { type: "Template" as const, id: templateId },
      ],
    }),
    generatePreview: builder.mutation<
      Response | string,
      { metadata: any; template_id: string }
    >({
      query: (body) => ({
        url: `/sourcing/rfp/documents/generate-stream`,
        method: "POST",
        body,
      }),
    }),

    // Enhance question answer API
    enhanceQuestionAnswer: builder.mutation<
      any,
      { questionId: string; prompt: string }
    >({
      query: ({ questionId, prompt }) => ({
        url: `/sourcing/rfp/questions/${questionId}/enhance`,
        method: "POST",
        body: { prompt },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { questionId }) => [
        { type: "Template" as const, id: "LIST" },
      ],
    }),

    // Generate answer for a specific question
    generateQuestionAnswer: builder.mutation<
      any,
      { questionId: string; sectionId: string; templateId: string }
    >({
      query: ({ questionId, sectionId, templateId }) => ({
        url: `/sourcing/rfp/questions/${questionId}/answer`,
        method: "POST",
        params: {
          section_id: sectionId,
          template_id: templateId,
        },
        headers: {
          accept: "application/json",
        },
      }),
      invalidatesTags: (result, error, { questionId }) => [
        { type: "Template" as const, id: "LIST" },
      ],
    }),
  }),
});

// Export hooks for usage in functional components, which are
// auto-generated based on the defined endpoints
export const {
  useGetSourcingCategoriesQuery,
  useGetAllRfpTemplatesQuery,
  useDownloadTemplateMutation,
  useUpdateTemplateNameMutation,
  useGetTemplateByIdQuery,
  useGenerateSubsectionQuestionsMutation,
  useGetExistingSubsectionQuestionsQuery,
  useGetPromptQuestionsMutation,
  useAcceptQuestionsMutation,
  useDeleteQuestionsMutation,
  useToggleKnowledgePalMutation,
  useDeleteDocumentMutation,
  useGenerateSectionAnswersMutation,
  useGetSectionAnswersQuery,
  useSaveAnswersMutation,
  useGeneratePreviewMutation,
  useGetAllTemplatesQuery,
  useEnhanceQuestionAnswerMutation,
  useGenerateQuestionAnswerMutation,
} = sourcingApi;

export const {
  useUploadDocumentMutation: useFormDataUploadDocumentMutation,
  useUploadTemplateMutation,
} = formDataApi;
