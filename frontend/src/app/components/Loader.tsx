interface LoaderProps {
  size?: "sm" | "md" | "lg" | "xl";
  color?: "blue" | "gray" | "white" | "purple" | "black";
}

export default function Loader({ size = "md", color = "blue" }: LoaderProps) {
  const sizeClasses = {
    sm: "w-5 h-5",
    md: "w-8 h-8", 
    lg: "w-12 h-12",
    xl: "w-16 h-16"
  };

  const colorClasses = {
    blue: "border-blue-500",
    gray: "border-gray-500",
    white: "border-white",
    purple: "border-purple-500",
    black: "border-black"
  };

  return (
    <div className="flex items-center justify-center">
      <div 
        className={`
          ${sizeClasses[size]} 
          ${colorClasses[color]}
          border-4 border-t-transparent 
          rounded-full 
          animate-spin
        `}
      />
    </div>
  );
}