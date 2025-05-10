import React, { useState } from 'react';
import { Box, Typography, Button, Paper, CircularProgress } from '@mui/material';

interface ActionRunnerProps {
  actionId: number;
  actionName: string;
}

const ActionRunner: React.FC<ActionRunnerProps> = ({ actionId, actionName }) => {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    // TODO: API-Call zur Ausführung der Action
    setTimeout(() => {
      setResult('Erfolgreich ausgeführt (Demo)');
      setRunning(false);
    }, 1500);
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle1">{actionName}</Typography>
      <Button variant="contained" onClick={handleRun} disabled={running} sx={{ mt: 1 }}>
        {running ? <CircularProgress size={20} /> : 'Action ausführen'}
      </Button>
      {result && <Typography sx={{ mt: 2 }}>{result}</Typography>}
    </Paper>
  );
};

export default ActionRunner; 