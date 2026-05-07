'use client';

import { useParams } from 'next/navigation';
import VerificationScreen from '@/components/hitl/VerificationScreen';

export default function VerifyCasePage() {
  const params = useParams();
  const caseId = params.caseId as string;

  if (!caseId) return null;

  return <VerificationScreen caseId={caseId} />;
}
