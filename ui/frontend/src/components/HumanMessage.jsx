import { User } from "lucide-react";

export default function HumanMessage({ message }) {
  return (
    <div className="message human-message">
      <div className="message-avatar human-avatar">
        <User size={18} />
      </div>
      <div className="message-body">
        <p>{message.content}</p>
      </div>
    </div>
  );
}
