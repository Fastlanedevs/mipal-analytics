import React from "react";
import { MessageSquare } from "lucide-react";

const Header = () => {
  return (
    <header className="p-4 text-white bg-blue-600 shadow-md">
      <div className="container flex items-center mx-auto">
        <MessageSquare className="w-8 h-8 mr-2" />
        <h1 className="text-2xl font-bold">MI Pal</h1>
      </div>
    </header>
  );
};

export default Header;
