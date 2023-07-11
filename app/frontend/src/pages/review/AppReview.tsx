import React from "react";
import { useRef, useState, useEffect, useMemo } from "react";
import {
    Checkbox,
    ChoiceGroup,
    IChoiceGroupOption,
    Panel,
    PrimaryButton,
    DefaultButton,
    Spinner,
    TextField,
    SpinButton,
    Slider,
    Toggle
} from "@fluentui/react";
import BootstrapTable from "@happymary16/react-bootstrap-table-next";
import { useId } from "@fluentui/react-hooks";

import "./AppReview.css";
import { Stack, IStackTokens } from "@fluentui/react";

import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example/ExampleListReview";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { Review } from "./Review";
import Masonry from "react-masonry-css";

import { AnswerIcon } from "../../components/Answer/AnswerIcon";

// Interface
export enum Platform {
    Android = "android",
    IOS = "ios"
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
    error?: string;
};

export type ReviewResponse = {
    answer: string;
    table: object;
    error?: string;
};

// API calls
export async function reviewTableApi(options: ReviewTableRequest): Promise<ReviewTableResponse> {
    const response = await fetch(`app_review/table/${options.platform}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    });

    const parsedResponse: ReviewTableResponse = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error("Sorry, we could not load the app review data, please try again.");
    }

    return parsedResponse;
}

export async function reviewApi(options: ReviewRequest): Promise<ReviewResponse> {
    const response = await fetch(`app_review/question/${options.platform}`, {
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
        throw Error("Sorry, we could not answer your question, please try again.");
    }

    return parsedResponse;
}

const interleave = (arr: string[], insert: any) => ([] as string[]).concat(...arr.map(n => [n, insert])).slice(0, -1);

const AppReview = () => {
    const [platform, setPlatform] = useState(Platform.Android);
    const [fetchTableApi, setFetchTableApi] = useState("");

    const tables = useRef({
        [Platform.Android]: null as any,
        [Platform.IOS]: null as any
    });

    const lastQuestionRef = useRef<string>("");
    const [showAsTable, setShowAsTable] = useState(false);

    const [table, _setTable] = useState<object>([]);
    const [answerTable, setAnswerTable] = useState<object>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<string>();
    const masonryBreakPoints = {
        default: 3,
        2700: 2,
        1100: 1
    };

    const setTable = (tableData: any) => {
        _setTable(
            tableData.map((t: any, i: number) => {
                return { ...t, id: i };
            })
        );
    };

    // API wrappers
    const loadTableApiRequest = async () => {
        error && setError(undefined);
        // setIsLoading(true);

        if (tables.current[platform] != null) {
            setTable(tables.current[platform]);
            return;
        }

        try {
            const request: ReviewTableRequest = {
                platform: platform
            };
            const result = await reviewTableApi(request);
            setTable(result.table);
            tables.current[platform] = result.table;
        } catch (e) {
            setError(e);
        } finally {
            // setIsLoading(false);
        }
    };

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);

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

    const renderReviews = (data: any) => {
        if (!data.length) return <></>;
        let review = data.map((r: any, i: number) => (
            <Review key={"review-" + r["id"]} comment={r["Body"]} date={r["Date"]} rating={r["Rating"]} version={r["Version"]} topics={r["topics"]} />
        ));
        return (
            <Masonry breakpointCols={masonryBreakPoints} className="masonryReviewGrid" columnClassName="masonryReviewColumn">
                {review}
            </Masonry>
        );
    };

    const renderTable = (data: any) => {
        if (!data.length) return <></>;

        const columns: object[] = Object.keys(data[0])
            .filter(k => k != "id")
            .map(k => {
                return {
                    dataField: k,
                    text: k
                };
            });

        return <BootstrapTable keyField="id" data={data} columns={columns} headerClasses="tableHeader" rowClasses="tableRow" className="table" />;
    };

    const switchDisplay = (e: any, checked: boolean | undefined) => {
        setShowAsTable(!!checked);
    };

    useEffect(() => {
        loadTableApiRequest();
    }, [platform]);

    const onExampleClicked = (example: string) => {
        makeApiRequest(example);
    };

    return (
        <div className="oneshotContainer">
            <div className="left-pane">
                <div className="controls">
                    <span>
                        {platform == Platform.Android ? (
                            <PrimaryButton text="Android" onClick={() => setPlatform(Platform.Android)} />
                        ) : (
                            <DefaultButton text="Android" onClick={() => setPlatform(Platform.Android)} />
                        )}
                        {platform == Platform.IOS ? (
                            <PrimaryButton text="iOS" onClick={() => setPlatform(Platform.IOS)} />
                        ) : (
                            <DefaultButton text="iOS" onClick={() => setPlatform(Platform.IOS)} />
                        )}
                    </span>
                    <span>
                        <Toggle className="toggle" onText="Showing as Table" offText="Showing as Reviews" onChange={switchDisplay} />
                    </span>
                </div>
                {showAsTable ? renderTable(table) : renderReviews(table)}
            </div>
            <div className="right-pane">
                <div className="oneshotTopSection">
                    <div className="oneshotQuestionInput">
                        <QuestionInput
                            placeholder="Example: What are the most common topics since 2023?"
                            disabled={isLoading}
                            onSend={question => makeApiRequest(question)}
                        />
                    </div>
                </div>
                <div className="oneshotBottomSection">
                    {isLoading && <Spinner label="Generating answer" />}
                    {!lastQuestionRef.current && <ExampleList onExampleClicked={onExampleClicked} />}
                    {!isLoading && answer && !error && (
                        <>
                            <div className="oneshotAnswerContainer">
                                <AnswerIcon />
                                <br />
                                {interleave(answer.split("\n"), <br />)}
                            </div>
                            <div style={{ overflow: "auto", width: "100%" }}>{renderTable(answerTable)}</div>
                        </>
                    )}
                    {error ? (
                        <div className="oneshotAnswerContainer">
                            <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current)} />
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    );
};

export default AppReview;
