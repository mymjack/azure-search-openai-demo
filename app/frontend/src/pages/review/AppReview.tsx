import React from "react";
import { useRef, useState, useEffect } from "react";
import { Checkbox, ChoiceGroup, IChoiceGroupOption, Panel, PrimaryButton, DefaultButton, Spinner, TextField, SpinButton, Slider } from "@fluentui/react";
import BootstrapTable from 'react-bootstrap-table-next'; 

import styles from "./AppReview.module.css";
import { Stack, IStackTokens } from '@fluentui/react';

import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { Review } from "./Review";

// Interface
export enum Platform {
    Android = 'android',
    IOS = 'ios'
} 

export type ReviewTableRequest = {
    platform: Platform;
};
export type ReviewRequest = {
    question: string;
    platform: Platform;
};

export type ReviewTableResponse = {
    table: object;
}

export type ReviewResponse = {
    answer: string;
    table: object;
}

// API calls
export async function reviewTableApi(options: ReviewTableRequest): Promise<ReviewTableResponse> {
    const response = await fetch(`http://localhost:5000/app_review/table/${options.platform}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    });

    const parsedResponse: ReviewTableResponse = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse;
}


export async function reviewApi(options: ReviewRequest): Promise<ReviewResponse> {
    const response = await fetch(`http://localhost:5000/app_review/question/${options.platform}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            question: options.question
        })
    });

    const parsedResponse: ReviewResponse = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse;
}


const AppReview = () => {
    const [platform, setPlatform] = useState(Platform.Android);

    const lastQuestionRef = useRef<string>("");

    const [table, setTable] = useState<object>({});
    const [answerTable, setAnswerTable] = useState<object>({});
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<string>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    // API wrappers
    const loadTableApiRequest = async () => {
        error && setError(undefined);
        // setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        try {
            const request: ReviewTableRequest = {
                platform: platform
            };
            const result = await reviewTableApi(request);
            setTable(result.table);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        try {
            const request: ReviewRequest = {
                question: question,
                platform: platform
            };
            const result = await reviewApi(request);
            setAnswer(result.answer);
            setAnswerTable(result.table);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const renderTable = (tableData) => {
        if (!tableData.length) return <></>;

        const columns : object[] = Object.keys(tableData[0]).map(k => { return {
            dataField: k,
            text: k
        }});

        return <BootstrapTable keyField='id' data={ tableData } columns={ columns } />
    }

    useEffect(() => {loadTableApiRequest()}, [platform]);
    useEffect(() => {loadTableApiRequest()}, []);

    const onExampleClicked = (example: string) => {
        makeApiRequest(example);
    };

    return (
        <div className={styles.oneshotContainer}>
            <Stack horizontal tokens={{childrenGap: 0, padding: 10}}>
                {platform == Platform.Android ?
                <PrimaryButton text="Android" 
                    onClick={() => setPlatform(Platform.Android)} />
                :<DefaultButton text="Android" 
                    onClick={() => setPlatform(Platform.Android)} />}
                {platform == Platform.IOS ?
                <PrimaryButton text="iOS" 
                    onClick={() => setPlatform(Platform.IOS)} />
                :<DefaultButton text="iOS" 
                    onClick={() => setPlatform(Platform.IOS)} />}
            </Stack>
            <div style={{maxHeight:'40vh',overflow:'auto',width: '100%'}}>
            {renderTable(table)}
            </div>
            <div className={styles.oneshotTopSection}>
                {/* <h1 className={styles.oneshotTitle}>Ask your data</h1> */}
                <div className={styles.oneshotQuestionInput}>
                    <QuestionInput
                        placeholder="Example: Does my plan cover annual eye exams?"
                        disabled={isLoading}
                        onSend={question => makeApiRequest(question)}
                    />
                </div>
            </div>
            <div className={styles.oneshotBottomSection}>
                {isLoading && <Spinner label="Generating answer" />}
                {!lastQuestionRef.current && <ExampleList onExampleClicked={onExampleClicked} />}
                {!isLoading && answer && !error && (
                    <div className={styles.oneshotAnswerContainer}>
                        {answer}
                    </div>
                )}
                {error ? (
                    <div className={styles.oneshotAnswerContainer}>
                        <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current)} />
                    </div>
                ) : null}
                
            <div style={{maxHeight:'40vh',overflow:'auto',width: '100%'}}>
            {renderTable(answerTable)}
            </div>
            </div>
            -- Below are WIP. Please discard--
            <Review comment="Hi, this is a reiview with comment"
                date="2022-01-02"
                rating="3"
                version="3.2"
                tags={['hi', 'b']}
                topics={['topic w', 'topic d']}
            />
        </div>
    );
};

export default AppReview;
