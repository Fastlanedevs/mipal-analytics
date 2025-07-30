import { Input } from "./ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import PhoneInput from "react-phone-input-2";
import "react-phone-input-2/lib/style.css";
import { useState, useEffect } from "react";
import { useTheme } from "next-themes";

interface Option {
  value: string;
  label: string;
  icon?: string;
}

interface FormFieldProps {
  label: string;
  id: string;
  disabled?: boolean;
  value: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  type?: "text" | "select" | "phone";
  options?: Option[];
}

export function FormField({
  label,
  id,
  disabled,
  value,
  onChange = () => {},
  placeholder,
  type = "text",
  options = [],
}: FormFieldProps) {
  // For phone input, we need to handle the formatted display value separately
  const [displayValue, setDisplayValue] = useState(value || "");
  const { theme } = useTheme();
  const isDarkMode = theme === "dark";

  // Update the display value when the value prop changes
  useEffect(() => {
    if (value !== undefined && value !== null) {
      setDisplayValue(value);
    }
  }, [value]);

  // Handle phone input change
  const handlePhoneChange = (val: string) => {
    setDisplayValue(val);
    onChange(val);
  };

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>

      {type === "select" ? (
        <Select disabled={disabled} value={value} onValueChange={onChange}>
          <SelectTrigger className="bg-transparent border-muted-foreground hover:border-muted-foreground  dark:border-muted-foreground/50 ">
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {options.map((option) => (
              <SelectItem
                key={option.value}
                value={option.value}
                className="cursor-pointer"
              >
                {option.icon && <span className="mr-2">{option.icon}</span>}
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : type === "phone" ? (
        <div className="phone-input-wrapper">
          <PhoneInput
            country={"us"}
            value={displayValue}
            onChange={handlePhoneChange}
            disabled={disabled}
            placeholder={placeholder}
            inputClass="w-full h-10 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50 bg-transparent"
            containerClass="w-full phone-input-container bg-transparent"
            buttonClass="hover:bg-accent hover:text-accent-foreground rounded-l-md h-10 bg-transparent active:bg-transparent focus:bg-transparent [&>.selected-flag]:!bg-transparent  [&>.selected-flag]:focus:!bg-transparent"
            dropdownClass="phone-dropdown bg-popover dark:bg-popover text-popover-foreground dark:text-popover-foreground [&>.country-list]:!bg-popover [&>.country-list_.country]:hover:!bg-accent/10 [&>.country-list_.country.highlight]:!bg-accent/10 [&>.country-list_.country]:data-[highlighted=true]:!bg-accent/10"
            buttonStyle={{
              border: "none",
              background: "transparent",
              // borderColor: isDarkMode ? 'hsl(var(--muted-foreground)/ 0)' : 'hsl(var(--muted-foreground))',
              // borderWidth: '1px',
              height: "36px",

              ...(disabled && {
                borderColor: isDarkMode
                  ? "hsl(var(--muted-foreground) / 0)"
                  : "hsl(var(--muted-foreground) / 0)",
                opacity: "0.7",
              }),
            }}
            inputStyle={{
              width: "100%",
              height: "36px",
              padding: "0px 0px 0px 44px",
              borderRadius: "0.375rem",
              background: "transparent",
              color: isDarkMode ? "hsl(var(--foreground))" : "inherit",
              borderColor: isDarkMode
                ? "hsl(var(--muted-foreground) / 0.5)"
                : "hsl(var(--muted-foreground))",
              outline: "none",
              boxShadow: "none",
              transition: "all 0.2s ease",
              // ...(disabled && {
              //   borderColor: isDarkMode ? 'hsl(var(--muted-foreground) / 0.3)' : 'hsl(var(--muted-foreground) / 0.5)',
              //   opacity: '0.7'
              // })
            }}
            containerStyle={{
              width: "100%",
              background: "transparent",
            }}
            dropdownStyle={{
              backgroundColor: "hsl(var(--popover))",
              color: "hsl(var(--popover-foreground))",
              // borderColor: isDarkMode ? 'hsl(var(--muted-foreground) / 0.5)' : 'hsl(var(--muted-foreground))',
              // borderWidth: '1px',
              // borderRadius: '0.375rem',
              ...(disabled && {
                borderColor: isDarkMode
                  ? "hsl(var(--muted-foreground) / 0.3)"
                  : "hsl(var(--muted-foreground) / 0.5)",
                opacity: "0.7",
              }),
            }}
            enableSearch={true}
            searchClass="!bg-popover dark:!bg-popover !text-popover-foreground dark:!text-popover-foreground !border-muted-foreground dark:!border-muted-foreground/50 !rounded-md !h-9 !px-3 !py-1 !text-sm"
            searchPlaceholder="Search country..."
            preferredCountries={["us", "gb", "ca", "au"]}
            autoFormat={false}
            countryCodeEditable={false}
            enableAreaCodes={true}
          />
        </div>
      ) : (
        <Input
          id={id}
          disabled={disabled}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      )}
    </div>
  );
}
