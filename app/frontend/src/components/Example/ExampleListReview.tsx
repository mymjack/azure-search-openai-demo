import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    { text: "What are the most common topics since 2023?", value: "What are the top 10 topics since 2023-01-01?" },
    { text: "What is the average rating of reviews since 2023?", value: "What is the average rating of reviews since 2023-01-01?" },
    { text: "What do customer say regarding login issues?", value: "What do customer say regarding login issues?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
