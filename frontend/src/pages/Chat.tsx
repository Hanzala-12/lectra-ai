import { LecturePicker } from '../components/LecturePicker';

export function Chat() {
  return (
    <LecturePicker
      title="Ask Your Lecture"
      subtitle="Pick a lecture to chat with (answers are grounded in its transcript)."
      tab="chat"
    />
  );
}
