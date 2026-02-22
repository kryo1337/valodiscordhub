import { useState } from "react";
import { Button, Input, Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui";

interface ScoreFormProps {
  onSubmit: (redScore: number, blueScore: number) => Promise<void>;
  isLoading?: boolean;
}

export function ScoreForm({ onSubmit, isLoading }: ScoreFormProps) {
  const [redScore, setRedScore] = useState("");
  const [blueScore, setBlueScore] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const red = parseInt(redScore, 10);
    const blue = parseInt(blueScore, 10);

    if (isNaN(red) || isNaN(blue)) {
      setError("Please enter valid scores");
      return;
    }

    if (red < 0 || blue < 0) {
      setError("Scores cannot be negative");
      return;
    }

    if (red === blue) {
      setError("Scores cannot be equal (no draws)");
      return;
    }

    try {
      await onSubmit(red, blue);
    } catch (err) {
      setError("Failed to submit score. Please try again.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submit Match Score</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Red Team Score"
              type="number"
              min="0"
              max="13"
              value={redScore}
              onChange={(e) => setRedScore(e.target.value)}
              placeholder="0"
            />
            <Input
              label="Blue Team Score"
              type="number"
              min="0"
              max="13"
              value={blueScore}
              onChange={(e) => setBlueScore(e.target.value)}
              placeholder="0"
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </CardContent>
        <CardFooter>
          <Button type="submit" className="w-full" isLoading={isLoading}>
            Submit Score
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
