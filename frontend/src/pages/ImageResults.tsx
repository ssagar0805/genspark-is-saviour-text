import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { analyzeImage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import TruthLensHeader from "@/components/TruthLensHeader";
import TruthLensFooter from "@/components/TruthLensFooter";
import {
  ArrowLeft,
  FileImage,
  Search,
  CheckCircle,
  Loader2,
  GraduationCap,
  Clock,
} from "lucide-react";

// Interface for navigation state
interface LocationState {
  file?: File;
  content_type?: string;
}

// Convert File to base64
const fileToBase64 = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

const ImageResults = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState) || {};

  if (!state?.file) {
    return <Navigate to="/" replace />;
  }

  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<null | {
    forensic: string;
    extracted_text: string;
    fact_check: string;
    education: string;
  }>(null);

  useEffect(() => {
    if (state.file) {
      const reader = new FileReader();
      reader.onload = () => setImagePreview(reader.result as string);
      reader.readAsDataURL(state.file);
      handleAnalyze();
    }
  }, [state.file]);

  const handleAnalyze = async () => {
    if (!state.file) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const imageBase64 = await fileToBase64(state.file);
      const res = await analyzeImage(imageBase64);
      setResults({
        forensic: res.forensic,
        extracted_text: res.ocr_text,
        fact_check: res.fact_check,
        education: res.education,
      });
    } catch (e: any) {
      console.error(e);
      setError("Image could not be analyzed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TruthLensHeader />
      <main className="flex-1">
        <section className="bg-gradient-to-br from-primary to-secondary border-b border-border">
          <div className="container mx-auto px-4 lg:px-6 py-6">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/")}
                className="text-white/90 hover:text-white hover:bg-white/10"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Image Analysis</h1>
                <div className="flex items-center gap-2 mt-1">
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-yellow-300" />
                      <span className="text-white/80 text-sm">Analyzing Image...</span>
                    </>
                  ) : results ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-300" />
                      <span className="text-white/80 text-sm">Analysis Complete</span>
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-white/60" />
                      <span className="text-white/80 text-sm">Preparing Analysis...</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="container mx-auto px-4 lg:px-6 py-8">
          <div className="max-w-4xl mx-auto space-y-6">
            <Card className="border-l-4 border-primary">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileImage className="w-5 h-5 text-primary" />
                  Uploaded Image
                </CardTitle>
              </CardHeader>
              <CardContent>
                {imagePreview && (
                  <div className="flex justify-center">
                    <img
                      src={imagePreview}
                      alt="Uploaded"
                      className="max-w-md max-h-80 object-contain rounded-lg border shadow-sm"
                    />
                  </div>
                )}
                <p className="text-sm text-center text-muted-foreground mt-4">
                  <strong>File:</strong> {state.file.name} (
                  {(state.file.size / 1024).toFixed(1)} KB)
                </p>
              </CardContent>
            </Card>

            {error && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="pt-6">
                  <div className="text-red-700 text-sm text-center">
                    <strong>Analysis Error:</strong> {error}
                    <Button onClick={handleAnalyze} className="ml-4" size="sm" variant="outline">
                      Retry
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {isAnalyzing && (
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-center gap-3 text-blue-700">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="font-medium">Analyzing image with AI...</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {results && (
              <>
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Search className="w-5 h-5 text-primary" />
                      <h3 className="font-semibold">🔬 Forensic Analysis</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{results.forensic}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <FileImage className="w-5 h-5 text-primary" />
                      <h3 className="font-semibold">📝 Text Extracted</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed font-medium">
                      "{results.extracted_text}"
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <h3 className="font-semibold">✅ Fact-Check Results</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{results.fact_check}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <GraduationCap className="w-5 h-5 text-primary" />
                      <h3 className="font-semibold">🎓 Education / Explanation</h3>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{results.education}</p>
                  </CardContent>
                </Card>
              </>
            )}

            <Card className="mt-8">
              <CardContent className="pt-6">
                <div className="flex justify-center">
                  <Button onClick={() => navigate("/")} variant="default" className="px-8">
                    <Search className="w-4 h-4 mr-2" />
                    Analyze Another
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
      <TruthLensFooter />
    </div>
  );
};

export default ImageResults;
