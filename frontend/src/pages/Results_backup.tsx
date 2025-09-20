import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import TruthLensHeader from "@/components/TruthLensHeader";
import TruthLensFooter from "@/components/TruthLensFooter";

const Results = () => {
  const navigate = useNavigate();

  // Mock analysis result data
  const analysisResult = {
    content: "Breaking: Government announces new tax policy affecting middle-class families...",
    riskLevel: "Medium",
    riskColor: "bg-amber-500/10 text-amber-600",
    credibilityScore: 72,
    sources: [
      { name: "Government Official Website", credibility: "High", verified: true },
      { name: "Local News Portal", credibility: "Medium", verified: true },
      { name: "Social Media Post", credibility: "Low", verified: false }
    ],
    flags: [
      { type: "Language Pattern", severity: "Low", description: "Sensational language detected" },
      { type: "Source Quality", severity: "Medium", description: "Mixed source credibility" }
    ],
    recommendations: [
      "Verify with official government sources",
      "Cross-check with multiple news outlets",
      "Look for official press releases"
    ]
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TruthLensHeader />
      <main className="flex-1">
        {/* Header */}
        <section className="bg-card border-b border-border">
          <div className="container mx-auto px-4 lg:px-6">
            <div className="flex items-center gap-4 py-6">
              <Button variant="ghost" onClick={() => navigate(-1)}>
                ← Back
              </Button>
              <h1 className="text-2xl font-bold text-foreground">Analysis Results</h1>
            </div>
          </div>
        </section>

        <div className="container mx-auto px-4 lg:px-6 py-8">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* Risk Assessment */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Risk Assessment</span>
                  <div className={`px-4 py-2 rounded-full text-sm font-semibold ${analysisResult.riskColor}`}>
                    {analysisResult.riskLevel} Risk
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-card-foreground mb-2">Credibility Score</h4>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-secondary/20 rounded-full h-3">
                        <div 
                          className={`h-3 rounded-full ${
                            analysisResult.credibilityScore >= 80 ? 'bg-green-500' :
                            analysisResult.credibilityScore >= 60 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${analysisResult.credibilityScore}%` }}
                        />
                      </div>
                      <span className="font-bold text-lg">{analysisResult.credibilityScore}%</span>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-card-foreground mb-2">Analysis Confidence</h4>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-secondary/20 rounded-full h-3">
                        <div 
                          className="h-3 rounded-full bg-truthlens-primary"
                          style={{ width: "87%" }}
                        />
                      </div>
                      <span className="font-bold text-lg">87%</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Content Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>Content Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-secondary/10 rounded-lg p-4 mb-6">
                  <h4 className="font-medium text-card-foreground mb-2">Analyzed Content:</h4>
                  <p className="text-muted-foreground italic">
                    "{analysisResult.content}"
                  </p>
                </div>

                {/* Flags */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-card-foreground">Detected Issues:</h4>
                  {analysisResult.flags.map((flag, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-card border border-border rounded-lg">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        flag.severity === 'High' ? 'bg-red-500' :
                        flag.severity === 'Medium' ? 'bg-amber-500' : 'bg-green-500'
                      }`} />
                      <div>
                        <div className="font-medium text-card-foreground">{flag.type}</div>
                        <div className="text-sm text-muted-foreground">{flag.description}</div>
                      </div>
                      <div className={`ml-auto px-2 py-1 rounded text-xs font-medium ${
                        flag.severity === 'High' ? 'bg-red-500/10 text-red-600' :
                        flag.severity === 'Medium' ? 'bg-amber-500/10 text-amber-600' : 
                        'bg-green-500/10 text-green-600'
                      }`}>
                        {flag.severity}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Source Verification */}
            <Card>
              <CardHeader>
                <CardTitle>Source Verification</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysisResult.sources.map((source, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-secondary/5 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${source.verified ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span className="font-medium text-card-foreground">{source.name}</span>
                      </div>
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                        source.credibility === 'High' ? 'bg-green-500/10 text-green-600' :
                        source.credibility === 'Medium' ? 'bg-amber-500/10 text-amber-600' :
                        'bg-red-500/10 text-red-600'
                      }`}>
                        {source.credibility} Credibility
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysisResult.recommendations.map((recommendation, index) => (
                    <div key={index} className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-truthlens-primary/10 text-truthlens-primary rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                        {index + 1}
                      </div>
                      <p className="text-muted-foreground">{recommendation}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" onClick={() => navigate("/")}>
                Analyze Another
              </Button>
              <Button size="lg" variant="outline">
                Report Issue
              </Button>
              <Button size="lg" variant="outline">
                Share Results
              </Button>
            </div>
          </div>
        </div>
      </main>
      <TruthLensFooter />
    </div>
  );
};

export default Results;