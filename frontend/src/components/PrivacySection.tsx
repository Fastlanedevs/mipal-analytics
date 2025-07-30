import React from "react";

interface SafeHTMLProps {
  html: string;
  className?: string;
}

const SafeHTML: React.FC<SafeHTMLProps> = ({ html, className }) => {
  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{
        __html: html,
      }}
    />
  );
};

const PrivacySection = ({
  title,
  subsections,
}: {
  title: string;
  subsections: any[];
}) => {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-semibold mb-4">{title}</h2>

      {subsections.map((subsection, index) => (
        <div key={index}>
          {subsection.subtitle && (
            <h3 className="text-lg font-medium mb-3">{subsection.subtitle}</h3>
          )}
          {subsection.description && (
            <p className="mb-2">
              <SafeHTML html={subsection.description} />
            </p>
          )}
          {subsection.items && (
            <ul className="list-disc pl-4 md:pl-6 mb-4">
              {subsection.items.map((item: string, itemIndex: number) => (
                <li key={itemIndex}>{item}</li>
              ))}
            </ul>
          )}
          {subsection.footerLine && <p>{subsection.footerLine}</p>}
        </div>
      ))}
    </section>
  );
};

export default PrivacySection;
