import { User } from "lucide-react";

export default function HumanMessage({ message }) {
  return (
    <div className="message human-message">
      <div className="human-bubble">
        <p>{message.content}</p>
      </div>
      <div className="message-avatar human-avatar">
        <User size={16} />
      </div>
    </div>
  );
}
